import { NextResponse, type NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login", "/register", "/landing"];

export function middleware(req: NextRequest) {
  const hasSession = req.cookies.has("access_token");
  const { pathname } = req.nextUrl;

  // Logged-in users never see auth/landing pages — everything funnels to the app.
  if (hasSession && (PUBLIC_PATHS.includes(pathname) || pathname === "/")) {
    const url = req.nextUrl.clone();
    url.pathname = "/dashboard";
    return NextResponse.redirect(url);
  }
  // Anonymous users get the public landing, never bare app routes or /login.
  if (!hasSession && !PUBLIC_PATHS.includes(pathname)) {
    const url = req.nextUrl.clone();
    url.pathname = "/landing";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|assets).*)"],
};
