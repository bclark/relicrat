const locationIdPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function locationId(value: string | string[] | undefined): string | undefined {
  return typeof value === 'string' && value.length === 36 && locationIdPattern.test(value) ? value : undefined;
}

export function locationLink(id?: string): string {
  return id ? `/?location=${encodeURIComponent(id)}` : '/';
}
