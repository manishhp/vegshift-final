export function capitalizeWords(value: string): string {
  if (!value) return value;
  return value
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

export function capitalizeList(values: string[]): string {
  return values.map(capitalizeWords).join(", ");
}
