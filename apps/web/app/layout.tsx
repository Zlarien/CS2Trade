import type { ReactNode } from "react";

export const metadata = {
  title: "CS2Trade",
  description: "Recommandations garder / vendre / trade-up pour ton inventaire CS2",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
