import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17211b",
        moss: "#335343",
        linen: "#f7f2e8",
        reed: "#d8e2d1",
        copper: "#b76e4c",
      },
      boxShadow: {
        panel: "0 18px 45px rgba(23, 33, 27, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;

