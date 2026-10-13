import type { Metadata, Viewport } from "next";
import "@fontsource-variable/newsreader/opsz.css";
import "@fontsource-variable/newsreader/opsz-italic.css";
import "@fontsource-variable/public-sans/wght.css";
import "@fontsource/young-serif/400.css";
import "@fontsource-variable/bricolage-grotesque/opsz.css";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

export const metadata: Metadata = {
  title: { default: "Launchcraft", template: "%s | Launchcraft" },
  description: "Turn a business idea into a store you can test, check and launch.",
};

export const viewport: Viewport = {
  themeColor: "#f7f4ee",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full">
      <body className="flex min-h-full flex-col">
        <TooltipProvider delayDuration={200}>
          {children}
          <Toaster theme="light" position="bottom-center" />
        </TooltipProvider>
      </body>
    </html>
  );
}
