import fs from 'node:fs';
import path from 'node:path';

function _toPosixPath(p) {
  return p.replaceAll(path.sep, '/');
}

export function getUiRootFromFilename(filename) {
  const normalized = filename.replaceAll('\\', '/');
  const marker = '/ui/';
  const candidates = [...normalized.matchAll(/\/ui\//g)].map((m) => m.index ?? -1);
  const validNext = new Set([
    'types',
    'lib',
    'hooks',
    'contexts',
    'components',
    'app',
    'eslint-rules',
    'scripts',
    'next.config.ts',
    'eslint.config.mjs',
  ]);

  for (const idx of candidates) {
    if (idx < 0) continue;
    const after = normalized.slice(idx + marker.length);
    const next = after.split('/')[0] ?? '';
    if (validNext.has(next)) {
      return normalized.slice(0, idx + marker.length - 1);
    }
  }

  return null;
}

export function normalizeFilename(filename) {
  return filename.replaceAll('\\', '/');
}

export function isUnderDir(filename, dirSuffixWithTrailingSlash) {
  const normalized = normalizeFilename(filename);
  return normalized.includes(dirSuffixWithTrailingSlash);
}

export function resolveImportToUiPath({ filename, importPath }) {
  const uiRoot = getUiRootFromFilename(filename);
  if (!uiRoot) return null;

  if (importPath.startsWith('@/')) {
    return _toPosixPath(path.join(uiRoot, importPath.slice(2)));
  }

  if (importPath.startsWith('./') || importPath.startsWith('../')) {
    const dir = path.dirname(filename);
    return _toPosixPath(path.resolve(dir, importPath));
  }

  return null;
}

function _candidatePathsWithoutExt(absPath) {
  const exts = ['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs'];
  return exts.map((ext) => `${absPath}${ext}`);
}

function _candidateIndexPaths(dirAbsPath) {
  const exts = ['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs'];
  return exts.map((ext) => _toPosixPath(path.join(dirAbsPath, `index${ext}`)));
}

export function resolveExistingFile(absPathNoQuery) {
  const absPath = absPathNoQuery.split('?')[0].split('#')[0];
  if (fs.existsSync(absPath) && fs.statSync(absPath).isFile()) {
    return _toPosixPath(absPath);
  }

  for (const candidate of _candidatePathsWithoutExt(absPath)) {
    if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
      return _toPosixPath(candidate);
    }
  }

  if (fs.existsSync(absPath) && fs.statSync(absPath).isDirectory()) {
    for (const indexCandidate of _candidateIndexPaths(absPath)) {
      if (fs.existsSync(indexCandidate) && fs.statSync(indexCandidate).isFile()) {
        return _toPosixPath(indexCandidate);
      }
    }
  }

  return _toPosixPath(absPath);
}

export function getUiRelativePathFromAbsolute(filenameAbs) {
  const uiRoot = getUiRootFromFilename(filenameAbs);
  if (!uiRoot) return null;
  const rel = path.relative(uiRoot, filenameAbs);
  return _toPosixPath(rel);
}

export function getUiLayerFromUiRelativePath(uiRelPath) {
  const rel = uiRelPath.replace(/^\.?\//, '');
  const top = rel.split('/')[0] ?? '';
  if (
    top === 'types' ||
    top === 'lib' ||
    top === 'hooks' ||
    top === 'contexts' ||
    top === 'components' ||
    top === 'app'
  ) {
    return top;
  }
  return null;
}
