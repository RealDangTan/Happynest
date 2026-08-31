import { Lora, Silkscreen } from "next/font/google";

export const silkscreen = Silkscreen({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-hn-pixel",
});

export const lora = Lora({
  subsets: ["latin", "vietnamese"],
  variable: "--font-hn-brand",
});
