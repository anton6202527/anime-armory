export type EditorBreadcrumbSymbolKind = "class" | "function" | "heading" | "property";

export type EditorBreadcrumbSymbol = {
  name: string;
  line: number;
  level: number;
  kind: EditorBreadcrumbSymbolKind;
};

export type BreadcrumbSymbolRequest = {
  id: number;
  name: string;
  text: string;
};

export type BreadcrumbSymbolResponse = {
  id: number;
  symbols: EditorBreadcrumbSymbol[];
};
