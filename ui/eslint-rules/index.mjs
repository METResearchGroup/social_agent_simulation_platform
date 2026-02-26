import {
  getUiLayerFromUiRelativePath,
  getUiRelativePathFromAbsolute,
  isUnderDir,
  normalizeFilename,
  resolveExistingFile,
  resolveImportToUiPath,
} from './utils/path.mjs';

function _walk(node, visitor) {
  if (!node || typeof node.type !== 'string') return;
  const shouldDescend = visitor(node);
  if (shouldDescend === false) return;

  for (const key of Object.keys(node)) {
    if (key === 'parent') continue;
    const value = node[key];
    if (Array.isArray(value)) {
      for (const child of value) _walk(child, visitor);
      continue;
    }
    if (value && typeof value.type === 'string') {
      _walk(value, visitor);
    }
  }
}

function _isFetchCallee(callee) {
  if (!callee) return false;
  if (callee.type === 'Identifier' && callee.name === 'fetch') return true;
  if (callee.type === 'MemberExpression' && !callee.computed) {
    const obj = callee.object;
    const prop = callee.property;
    if (prop?.type === 'Identifier' && prop.name === 'fetch') {
      if (obj?.type === 'Identifier' && (obj.name === 'globalThis' || obj.name === 'window')) {
        return true;
      }
    }
  }
  return false;
}

function _isProcessEnvMemberExpression(node) {
  return (
    node.type === 'MemberExpression' &&
    node.computed === false &&
    node.object?.type === 'Identifier' &&
    node.object.name === 'process' &&
    node.property?.type === 'Identifier' &&
    node.property.name === 'env'
  );
}

function _isUseEffectCallee(callee) {
  if (!callee) return false;
  if (callee.type === 'Identifier' && callee.name === 'useEffect') return true;
  if (callee.type === 'MemberExpression' && !callee.computed) {
    const obj = callee.object;
    const prop = callee.property;
    if (obj?.type === 'Identifier' && obj.name === 'React') {
      return prop?.type === 'Identifier' && prop.name === 'useEffect';
    }
  }
  return false;
}

function _getImportSourceValue(node) {
  if (!node?.source) return null;
  if (typeof node.source.value === 'string') return node.source.value;
  return null;
}

function _getUiLayerForFilename(filename) {
  const abs = normalizeFilename(filename);
  const rel = getUiRelativePathFromAbsolute(abs);
  if (!rel) return null;
  return getUiLayerFromUiRelativePath(rel);
}

function _resolveImportTargetLayer({ filename, importPath }) {
  const abs = resolveImportToUiPath({ filename, importPath });
  if (!abs) return null;
  const resolved = resolveExistingFile(abs);
  const rel = getUiRelativePathFromAbsolute(resolved);
  if (!rel) return null;
  return getUiLayerFromUiRelativePath(rel);
}

const LAYER_ORDER = {
  types: 0,
  lib: 1,
  hooks: 2,
  contexts: 3,
  components: 4,
  app: 5,
};

function _isLayeringViolation(fromLayer, toLayer) {
  if (fromLayer === 'app') return false;
  if (!(fromLayer in LAYER_ORDER) || !(toLayer in LAYER_ORDER)) {
    // This should never happen because we compute layers from a fixed allowlist. If it does,
    // keep it visible during lint runs to make misconfigurations obvious.
    console.warn('[ui-import-layering] Unknown layer', { fromLayer, toLayer });
    return false;
  }
  return LAYER_ORDER[toLayer] > LAYER_ORDER[fromLayer];
}

function _containsAwaitAndSetStateCall(asyncFnNode) {
  // Heuristic: treat any call to an identifier matching /^set[A-Z]/ as a "setState" call.
  // This is intentionally lightweight and may have false positives (e.g. setProperty())
  // and false negatives (e.g. aliased setters like updateCount = setCount). If this
  // becomes noisy, we can improve it with scope analysis (context.getScope()) to resolve
  // identifier bindings back to React state setters.
  let hasAwait = false;
  let hasSetStateCall = false;

  _walk(asyncFnNode.body, (node) => {
    if (
      node.type === 'FunctionDeclaration' ||
      node.type === 'FunctionExpression' ||
      node.type === 'ArrowFunctionExpression'
    ) {
      if (node !== asyncFnNode) return false;
    }

    if (node.type === 'AwaitExpression') {
      hasAwait = true;
      return;
    }

    if (node.type === 'CallExpression' && node.callee?.type === 'Identifier') {
      if (/^set[A-Z]/.test(node.callee.name)) {
        hasSetStateCall = true;
      }
    }
  });

  return hasAwait && hasSetStateCall;
}

function _effectNeedsRequestIdGuard(effectCallbackBodyNode, depsNode) {
  if (depsNode?.type === 'ArrayExpression' && depsNode.elements.length === 0) return false;
  if (!effectCallbackBodyNode || effectCallbackBodyNode.type !== 'BlockStatement') return false;

  const asyncFns = [];
  _walk(effectCallbackBodyNode, (node) => {
    if (
      (node.type === 'FunctionDeclaration' || node.type === 'FunctionExpression' || node.type === 'ArrowFunctionExpression') &&
      node.async === true
    ) {
      asyncFns.push(node);
    }
  });

  return asyncFns.some(_containsAwaitAndSetStateCall);
}

function _hasRequestIdGuard(effectCallbackBodyNode) {
  if (!effectCallbackBodyNode || effectCallbackBodyNode.type !== 'BlockStatement') return false;

  const capturedRefs = new Set();
  const incrementedRefs = new Set();
  const guardedRefs = new Set();
  const mapSetRefs = new Set();
  const mapGuardedRefs = new Set();

  _walk(effectCallbackBodyNode, (node) => {
    if (
      node.type === 'VariableDeclarator' &&
      node.id?.type === 'Identifier' &&
      node.id.name === 'requestId' &&
      node.init?.type === 'MemberExpression' &&
      node.init.computed === false &&
      node.init.object?.type === 'Identifier' &&
      node.init.property?.type === 'Identifier' &&
      node.init.property.name === 'current'
    ) {
      capturedRefs.add(node.init.object.name);
    }

    if (node.type === 'UpdateExpression' && (node.operator === '++' || node.operator === '--')) {
      const arg = node.argument;
      if (
        arg?.type === 'MemberExpression' &&
        arg.computed === false &&
        arg.object?.type === 'Identifier' &&
        arg.property?.type === 'Identifier' &&
        arg.property.name === 'current'
      ) {
        incrementedRefs.add(arg.object.name);
      }
    }

    if (node.type === 'AssignmentExpression' && node.left?.type === 'MemberExpression') {
      const left = node.left;
      if (
        left.computed === false &&
        left.object?.type === 'Identifier' &&
        left.property?.type === 'Identifier' &&
        left.property.name === 'current'
      ) {
        if (node.operator === '+=') {
          incrementedRefs.add(left.object.name);
        }
        if (node.operator === '=' && node.right?.type === 'BinaryExpression' && node.right.operator === '+') {
          incrementedRefs.add(left.object.name);
        }
      }
    }

    if (node.type === 'IfStatement' && node.test?.type === 'BinaryExpression' && node.test.operator === '!==') {
      const left = node.test.left;
      const right = node.test.right;
      const returnInConsequent =
        node.consequent?.type === 'ReturnStatement' ||
        (node.consequent?.type === 'BlockStatement' &&
          node.consequent.body.some((stmt) => stmt.type === 'ReturnStatement'));
      if (!returnInConsequent) return;

      const pairs = [
        [left, right],
        [right, left],
      ];
      for (const [a, b] of pairs) {
        if (a?.type !== 'Identifier' || a.name !== 'requestId') continue;
        if (
          b?.type === 'MemberExpression' &&
          b.computed === false &&
          b.object?.type === 'Identifier' &&
          b.property?.type === 'Identifier' &&
          b.property.name === 'current'
        ) {
          guardedRefs.add(b.object.name);
        }

        if (
          b?.type === 'CallExpression' &&
          b.callee?.type === 'MemberExpression' &&
          b.callee.computed === false &&
          b.callee.object?.type === 'MemberExpression' &&
          b.callee.object.computed === false &&
          b.callee.object.object?.type === 'Identifier' &&
          b.callee.object.property?.type === 'Identifier' &&
          b.callee.object.property.name === 'current' &&
          b.callee.property?.type === 'Identifier' &&
          b.callee.property.name === 'get'
        ) {
          mapGuardedRefs.add(b.callee.object.object.name);
        }
      }
    }

    if (
      node.type === 'CallExpression' &&
      node.callee?.type === 'MemberExpression' &&
      node.callee.computed === false &&
      node.callee.object?.type === 'MemberExpression' &&
      node.callee.object.computed === false &&
      node.callee.object.object?.type === 'Identifier' &&
      node.callee.object.property?.type === 'Identifier' &&
      node.callee.object.property.name === 'current' &&
      node.callee.property?.type === 'Identifier' &&
      node.callee.property.name === 'set'
    ) {
      const args = node.arguments ?? [];
      if (args.length >= 2 && args[1]?.type === 'Identifier' && args[1].name === 'requestId') {
        mapSetRefs.add(node.callee.object.object.name);
      }
    }
  });

  for (const refName of capturedRefs) {
    if (incrementedRefs.has(refName) && guardedRefs.has(refName)) {
      return true;
    }
  }
  for (const refName of mapSetRefs) {
    if (mapGuardedRefs.has(refName)) return true;
  }
  return false;
}

const rules = {
  'no-fetch-outside-api': {
    meta: {
      type: 'problem',
      docs: { description: 'Disallow fetch() outside ui/lib/api.' },
      schema: [],
      messages: {
        noFetch: 'Only ui/lib/api/** may call fetch(). Route network calls through the API client layer.',
      },
    },
    create(context) {
      const filename = normalizeFilename(context.getFilename());
      const allowed = isUnderDir(filename, '/ui/lib/api/');
      return {
        CallExpression(node) {
          if (allowed) return;
          if (_isFetchCallee(node.callee)) {
            context.report({ node, messageId: 'noFetch' });
          }
        },
      };
    },
  },

  'no-process-env-outside-boundaries': {
    meta: {
      type: 'problem',
      docs: { description: 'Disallow process.env access outside approved boundaries.' },
      schema: [],
      messages: {
        noEnv:
          'Do not read process.env outside ui/next.config.ts, ui/lib/**, or ui/scripts/**. Add an explicit env boundary module.',
      },
    },
    create(context) {
      const filename = normalizeFilename(context.getFilename());
      const allow =
        filename.endsWith('/ui/next.config.ts') ||
        isUnderDir(filename, '/ui/lib/') ||
        isUnderDir(filename, '/ui/scripts/');
      return {
        MemberExpression(node) {
          if (allow) return;
          if (_isProcessEnvMemberExpression(node)) {
            context.report({ node, messageId: 'noEnv' });
          }
        },
      };
    },
  },

  'supabase-auth-boundary': {
    meta: {
      type: 'problem',
      docs: { description: 'Forbid importing supabase singleton outside AuthContext.' },
      schema: [],
      messages: {
        noSupabase:
          'Do not import { supabase } outside ui/contexts/AuthContext.tsx; use useAuth() and AuthContext methods instead.',
      },
    },
    create(context) {
      const filename = normalizeFilename(context.getFilename());
      const allow =
        filename.endsWith('/ui/contexts/AuthContext.tsx') || filename.endsWith('/ui/lib/supabase.ts');

      return {
        ImportDeclaration(node) {
          if (allow) return;
          const sourceValue = _getImportSourceValue(node);
          if (sourceValue == null) return;

          const abs = resolveImportToUiPath({ filename, importPath: sourceValue });
          if (!abs) return;
          const resolved = resolveExistingFile(abs);
          const rel = getUiRelativePathFromAbsolute(resolved);
          const isSupabaseModule = rel != null && /^lib\/supabase(\.[cm]?[jt]sx?)?$/.test(rel);
          if (!isSupabaseModule) return;

          const importsSupabase = node.specifiers.some(
            (s) => s.type === 'ImportSpecifier' && s.imported?.type === 'Identifier' && s.imported.name === 'supabase',
          );
          if (!importsSupabase) return;

          context.report({ node, messageId: 'noSupabase' });
        },
      };
    },
  },

  'useeffect-requires-request-id-guard': {
    meta: {
      type: 'problem',
      docs: {
        description:
          'Require request-id guard for rerunnable async useEffects that set state after await. Heuristic: detects setters via /^set[A-Z]/ in _containsAwaitAndSetStateCall; may miss aliases and may false-positive on non-React helpers.',
      },
      schema: [],
      messages: {
        needGuard:
          'This useEffect can re-run and sets state after await; add a request-id guard (ref.current increment + captured requestId + return-if-stale checks).',
      },
    },
    create(context) {
      return {
        CallExpression(node) {
          if (!_isUseEffectCallee(node.callee)) return;
          const [callback, deps] = node.arguments;
          if (!callback || (callback.type !== 'ArrowFunctionExpression' && callback.type !== 'FunctionExpression')) return;

          const body = callback.body;
          if (!_effectNeedsRequestIdGuard(body, deps)) return;
          if (_hasRequestIdGuard(body)) return;

          context.report({ node, messageId: 'needGuard' });
        },
      };
    },
  },

  'ui-import-layering': {
    meta: {
      type: 'problem',
      docs: { description: 'Enforce ui layering boundaries (types/lib/hooks/contexts/components/app).' },
      schema: [],
      messages: {
        layering:
          'Import violates UI layering: {{fromLayer}} must not import from {{toLayer}}. Keep dependencies flowing types → lib → hooks → contexts → components → app.',
      },
    },
    create(context) {
      const filename = normalizeFilename(context.getFilename());
      const fromLayer = _getUiLayerForFilename(filename);
      if (!fromLayer) return {};

      return {
        ImportDeclaration(node) {
          const sourceValue = _getImportSourceValue(node);
          if (sourceValue == null) return;
          const targetLayer = _resolveImportTargetLayer({ filename, importPath: sourceValue });
          if (!targetLayer) return;
          if (_isLayeringViolation(fromLayer, targetLayer)) {
            context.report({
              node,
              messageId: 'layering',
              data: { fromLayer, toLayer: targetLayer },
            });
          }
        },
      };
    },
  },
};

const localEslintRulesPlugin = { rules };
export default localEslintRulesPlugin;
