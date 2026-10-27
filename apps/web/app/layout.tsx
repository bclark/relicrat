import type { ReactNode } from "react";

export const metadata = {
  title: "RelicRat",
  description: "Your collection, your story.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: "3rem auto", maxWidth: 720, padding: "0 1rem" }}>
        {children}
      </body>
    </html>
  );
}
