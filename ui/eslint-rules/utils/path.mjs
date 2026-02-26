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

function _isFile(p) {
  try {
    return fs.statSync(p).isFile();
  } catch {
    return false;
  }
}

function _isDirectory(p) {
  try {
    return fs.statSync(p).isDirectory();
  } catch {
    return false;
  }
}

export function resolveExistingFile(absPathNoQuery) {
  const absPath = absPathNoQuery.split('?')[0].split('#')[0];
  if (_isFile(absPath)) {
    return _toPosixPath(absPath);
  }

  for (const candidate of _candidatePathsWithoutExt(absPath)) {
    if (_isFile(candidate)) {
      return _toPosixPath(candidate);
    }
  }

  if (_isDirectory(absPath)) {
    for (const indexCandidate of _candidateIndexPaths(absPath)) {
      if (_isFile(indexCandidate)) {
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
