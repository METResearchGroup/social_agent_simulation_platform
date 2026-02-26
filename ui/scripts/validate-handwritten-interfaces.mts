import path from 'node:path';
import { fileURLToPath } from 'node:url';

import ts from 'typescript';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const uiRoot = path.resolve(__dirname, '..');
const tsConfigPath = path.join(uiRoot, 'tsconfig.json');

const configFile = ts.readConfigFile(tsConfigPath, ts.sys.readFile);
if (configFile.error) {
  throw new Error(ts.formatDiagnosticsWithColorAndContext([configFile.error], {
    getCurrentDirectory: () => uiRoot,
    getCanonicalFileName: (fileName) => fileName,
    getNewLine: () => ts.sys.newLine,
  }));
}

const parsedConfig = ts.parseJsonConfigFileContent(
  configFile.config,
  ts.sys,
  uiRoot,
  undefined,
  tsConfigPath,
);

const program = ts.createProgram({
  rootNames: parsedConfig.fileNames,
  options: parsedConfig.options,
});
const checker = program.getTypeChecker();

const interfaceFilePath = path.join(uiRoot, 'types/index.ts');
const schemaFilePath = path.join(uiRoot, 'types/api.generated.ts');

const interfaceSource = program.getSourceFile(interfaceFilePath);
if (!interfaceSource) {
  throw new Error(`Unable to load ${interfaceFilePath}`);
}

const schemaSource = program.getSourceFile(schemaFilePath);
if (!schemaSource) {
  throw new Error(`Unable to load ${schemaFilePath}`);
}

interface MappingConfig {
  interfaceName: string;
  schemaName: string;
  ignoreInterfaceProperties?: string[];
  ignoreSchemaProperties?: string[];
  optionalityExceptions?: string[];
  skipPropertyTypeChecks?: string[];
}

const mappings: MappingConfig[] = [
  { interfaceName: 'Run', schemaName: 'RunListItem' },
  { interfaceName: 'Agent', schemaName: 'AgentSchema' },
  { interfaceName: 'Post', schemaName: 'PostSchema' },
  { interfaceName: 'Feed', schemaName: 'FeedSchema' },
  { interfaceName: 'AgentAction', schemaName: 'AgentActionSchema' },
  {
    interfaceName: 'Turn',
    schemaName: 'TurnSchema',
    skipPropertyTypeChecks: ['agentFeeds', 'agentActions'],
  },
  { interfaceName: 'FeedAlgorithm', schemaName: 'FeedAlgorithmSchema' },
  { interfaceName: 'Metric', schemaName: 'MetricSchema' },
  {
    interfaceName: 'RunConfig',
    schemaName: 'RunConfigDetail',
    ignoreInterfaceProperties: ['feedAlgorithmConfig'],
    optionalityExceptions: ['metricKeys'],
    skipPropertyTypeChecks: ['metricKeys'],
  },
];

const componentsSymbol = getExportedSymbol(schemaSource, 'components');
const componentsType = checker.getDeclaredTypeOfSymbol(componentsSymbol);
const schemasProperty = componentsType.getProperty('schemas');
if (!schemasProperty) {
  throw new Error('Unable to locate components.schemas in generated API file');
}
const schemasDeclaration =
  schemasProperty.valueDeclaration ?? schemasProperty.declarations?.[0];
if (!schemasDeclaration) {
  throw new Error('components.schemas has no declaration to inspect');
}
const schemasType = checker.getTypeOfSymbolAtLocation(schemasProperty, schemasDeclaration);

const validationErrors: string[] = [];

for (const mapping of mappings) {
  try {
    validateMapping(mapping);
  } catch (error) {
    validationErrors.push(error instanceof Error ? error.message : `${error}`);
  }
}

if (validationErrors.length > 0) {
  console.error('Interface validation against generated schemas failed:');
  for (const message of validationErrors) {
    console.error(message);
  }
  process.exitCode = 1;
} else {
  console.log('Handwritten interfaces are in sync with the generated schemas.');
}

function validateMapping(mapping: MappingConfig): void {
  const interfaceSymbol = getExportedSymbol(interfaceSource, mapping.interfaceName);
  const interfaceType = checker.getDeclaredTypeOfSymbol(interfaceSymbol);

  const schemaSymbol = getSchemaProperty(mapping.schemaName);
  const schemaType = checker.getTypeOfSymbolAtLocation(
    schemaSymbol,
    schemaSymbol.valueDeclaration ?? schemaSymbol.declarations?.[0],
  );

  const interfaceProperties = buildPropertyMap(interfaceType, (name) => toSnakeCase(name));
  const schemaProperties = buildPropertyMap(schemaType, (name) => normalizeSchemaName(name));

  const propertyErrors: string[] = [];
  const matchedSchemaProperties = new Set<string>();

  for (const property of interfaceProperties.values()) {
    if (mapping.ignoreInterfaceProperties?.includes(property.name)) {
      continue;
    }

    const schemaProperty = schemaProperties.get(property.normalizedName);
    if (!schemaProperty) {
      propertyErrors.push(
        `Interface '${mapping.interfaceName}' property '${property.name}' has no matching schema property named '${property.normalizedName}' in '${mapping.schemaName}'`,
      );
      continue;
    }

    matchedSchemaProperties.add(schemaProperty.normalizedName);

    if (
      !mapping.optionalityExceptions?.includes(property.name) &&
      property.optional !== schemaProperty.optional
    ) {
      propertyErrors.push(
        `Optionality mismatch for '${property.name}' (${mapping.interfaceName}) vs '${schemaProperty.name}' (${mapping.schemaName}): interface=${
          property.optional ? 'optional' : 'required'
        }, schema=${schemaProperty.optional ? 'optional' : 'required'}`,
      );
    }

    const skipTypeCheck = mapping.skipPropertyTypeChecks?.includes(property.name);
    if (!skipTypeCheck) {
      const interfaceComparableType = property.optional
        ? checker.getNonNullableType(property.type)
        : property.type;
      const schemaComparableType = schemaProperty.optional
        ? checker.getNonNullableType(schemaProperty.type)
        : schemaProperty.type;

      if (!checker.isTypeAssignableTo(interfaceComparableType, schemaComparableType)) {
        propertyErrors.push(
          `Type mismatch: interface '${mapping.interfaceName}'.${property.name} (${checker.typeToString(
            interfaceComparableType,
          )}) is not assignable to schema '${mapping.schemaName}'.${schemaProperty.name} (${checker.typeToString(
            schemaComparableType,
          )})`,
        );
      }

      if (!checker.isTypeAssignableTo(schemaComparableType, interfaceComparableType)) {
        propertyErrors.push(
          `Type mismatch: schema '${mapping.schemaName}'.${schemaProperty.name} (${checker.typeToString(
            schemaComparableType,
          )}) is not assignable to interface '${mapping.interfaceName}'.${property.name} (${checker.typeToString(
            interfaceComparableType,
          )})`,
        );
      }
    }
  }

  for (const schemaProperty of schemaProperties.values()) {
    if (matchedSchemaProperties.has(schemaProperty.normalizedName)) {
      continue;
    }
    if (mapping.ignoreSchemaProperties?.includes(schemaProperty.name)) {
      continue;
    }
    propertyErrors.push(
      `Schema '${mapping.schemaName}' property '${schemaProperty.name}' (${schemaProperty.normalizedName}) is missing in interface '${mapping.interfaceName}'`,
    );
  }

  if (propertyErrors.length > 0) {
    throw new Error(
      `Validation failed for ${mapping.interfaceName} vs ${mapping.schemaName}:
  - ${propertyErrors.join('\n  - ')}`,
    );
  }
}

function buildPropertyMap(
  type: ts.Type,
  normalize: (name: string) => string,
): Map<string, { name: string; normalizedName: string; optional: boolean; type: ts.Type }> {
  const map = new Map<string, { name: string; normalizedName: string; optional: boolean; type: ts.Type }>();

  for (const symbol of type.getProperties()) {
    const declaration = symbol.valueDeclaration ?? symbol.declarations?.[0];
    if (!declaration) {
      continue;
    }

    if (!ts.isPropertySignature(declaration) && !ts.isPropertyDeclaration(declaration)) {
      continue;
    }

    const name = symbol.getName();
    const normalizedName = normalize(name);
    if (map.has(normalizedName)) {
      throw new Error(
        `Duplicate property name '${name}' (normalized to '${normalizedName}') in type '${checker.typeToString(type)}'`,
      );
    }

    const typeAtLocation = checker.getTypeOfSymbolAtLocation(symbol, declaration);
    const optional = Boolean(symbol.flags & ts.SymbolFlags.Optional) || Boolean(declaration.questionToken);

    map.set(normalizedName, { name, normalizedName, optional, type: typeAtLocation });
  }

  return map;
}

function getSchemaProperty(schemaName: string): ts.Symbol {
  const property = schemasType.getProperty(schemaName);
  if (!property) {
    throw new Error(`Schema '${schemaName}' was not found on components.schemas`);
  }
  return property;
}

function getExportedSymbol(sourceFile: ts.SourceFile, name: string): ts.Symbol {
  const symbol = checker.getSymbolAtLocation(sourceFile);
  if (!symbol) {
    throw new Error(`Unable to get module symbol for ${sourceFile.fileName}`);
  }

  const exports = symbol.exports;
  if (!exports) {
    throw new Error(`Source file ${sourceFile.fileName} has no exports to inspect`);
  }

  const exported = exports.get(ts.escapeLeadingUnderscores(name) as ts.__String);
  if (!exported) {
    throw new Error(`Export '${name}' was not found in ${sourceFile.fileName}`);
  }

  return exported;
}

function normalizeSchemaName(name: string): string {
  return name;
}

function toSnakeCase(value: string): string {
  return value
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .replace(/([A-Z])([A-Z][a-z])/g, '$1_$2')
    .replace(/-/g, '_')
    .toLowerCase();
}
