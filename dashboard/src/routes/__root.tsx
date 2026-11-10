import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  useRouterState,
  HeadContent,
  Scripts,
  type ErrorComponentProps,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";
import { Activity, BarChart3, FileCheck2, ShoppingBag } from "lucide-react";

import appCss from "../styles.css?url";
import { reportLovableError } from "../lib/lovable-error-reporting";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">Page not found</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: ErrorComponentProps) {
  console.error(error);
  const router = useRouter();
  useEffect(() => {
    reportLovableError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">
          This page didn't load
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Something went wrong on our end. You can try refreshing or head back home.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Try again
          </button>
          <a
            href="/"
            className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    // Each leaf page sets specific metadata. The root supplies no inherited social image.
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "Trussted" },
      { name: "description", content: "An evidence dashboard for runs, shopping, receipts, and benchmark results." },
      { name: "author", content: "Trussted" },
      { property: "og:title", content: "Trussted" },
      { property: "og:description", content: "An evidence dashboard for runs, shopping, receipts, and benchmark results." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:site", content: "@Lovable" },
    ],
    links: [
      {
        rel: "stylesheet",
        href: appCss,
      },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap",
      },
      { rel: "icon", href: "/favicon.ico", type: "image/x-icon" },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const activeScreen = pathname === "/chat" ? "Shop" : pathname === "/receipts" ? "Receipts" : pathname === "/benchmark" ? "Benchmark" : "Runs";
  const navItems = [
    { label: "Runs", to: "/", icon: Activity },
    { label: "Shop", to: "/chat", icon: ShoppingBag },
    { label: "Receipts", to: "/receipts", icon: FileCheck2 },
    { label: "Benchmark", to: "/benchmark", icon: BarChart3 },
  ] as const;

  return (
    <QueryClientProvider client={queryClient}>
      <div className="app-frame">
        <aside className="app-sidebar" aria-label="Main navigation">
          <Link to="/" className="brand-lockup" aria-label="Trussted home">
            <span className="brand-mark" aria-hidden="true">T</span>
            <span>Trussted</span>
          </Link>
          <div className="sidebar-caption">WORKSPACE</div>
          <nav className="app-nav">
            {navItems.map(({ label, to, icon: Icon }) => (
              <Link
                key={label}
                to={to}
                activeOptions={{ exact: to === "/" }}
                className="nav-link"
                activeProps={{ className: "nav-link nav-link-active" }}
                aria-current={activeScreen === label ? "page" : undefined}
              >
                <Icon aria-hidden="true" />
                <span>{label}</span>
              </Link>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <span className="demo-dot" aria-hidden="true" />
            <span>Sample workspace</span>
            <span className="sidebar-version">v0.1</span>
          </div>
        </aside>
        <main className="app-main">
          <div className="mobile-topbar">
            <Link to="/" className="brand-lockup" aria-label="Trussted home">
              <span className="brand-mark" aria-hidden="true">T</span>
              <span>Trussted</span>
            </Link>
            <span className="mobile-screen-name">{activeScreen}</span>
          </div>
          <nav className="mobile-nav" aria-label="Main navigation">
            {navItems.map(({ label, to, icon: Icon }) => (
              <Link key={label} to={to} activeOptions={{ exact: to === "/" }} className="mobile-nav-link" activeProps={{ className: "mobile-nav-link mobile-nav-link-active" }} aria-current={activeScreen === label ? "page" : undefined}>
                <Icon aria-hidden="true" /><span>{label}</span>
              </Link>
            ))}
          </nav>
          <div className="page-wrap">
            <div className="limitations-banner" role="note">
              <span className="banner-dot" aria-hidden="true" />
              <p><strong>Illustrative data.</strong> Sample results only; no live store, run source, or receipt verification is connected.</p>
              <Link to="/benchmark" hash="limitations" className="banner-link">Known limitations <span aria-hidden="true">↗</span></Link>
            </div>
            {/* Keep one main landmark here; child pages render their content in this outlet. */}
            <Outlet />
            <footer className="page-footer">Trussted <span aria-hidden="true">·</span> Sample workspace <span aria-hidden="true">·</span> Results shown are illustrative</footer>
          </div>
        </main>
      </div>
    </QueryClientProvider>
  );
}
