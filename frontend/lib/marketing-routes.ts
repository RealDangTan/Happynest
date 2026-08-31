export const PUBLIC_PATHS = [
  "/login",
  "/register",
  "/landing",
  "/product",
  "/company",
  "/blog",
  "/docs",
  "/qna",
  "/legal",
] as const;

export function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );
}

