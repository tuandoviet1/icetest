/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./components/**/*.{ts,tsx}", "./pages/**/*.{ts,tsx}"],
  variants: {
    extend: {
      visibility: ["group-hover"],
      backgroundColor: ["group-hover"],
    },
  },
  theme: {
    extend: {
      width: {
        140: "35rem",
      },
      screens: {
        "has-hover": { raw: "(hover: hover)" },
      },
      flex: {
        2: "2 2 0%",
        3: "3 3 0%",
      },
    },
    colors: {
      transparent: "transparent",
      current: "currentColor",
      white: "#ffffff",
      slate: {
        50: "#F9FAFB",
        100: "#F1F5F9",
        200: "#E2E8F0",
        300: "#CBD5E1",
        400: "#94A3B8",
        500: "#64748B",
        600: "#475569",
        700: "#334155",
        800: "#1E293B",
        900: "#0F172A",
      },
      gray: {
        50: "#FAFCFC",
        100: "#F7F9FC",
        200: "#DFE3E9",
        300: "#C7CDD5",
        400: "#AFB7C2",
        500: "#98A2AF",
        600: "#788492",
        700: "#596676",
        800: "#3A485A",
        900: "#1B2B3E",
      },
      blue: {
        50: "#F9FBFF",
        100: "#F3F8FF",
        150: "#DDECFE",
        200: "#C8E0FE",
        300: "#A4CBFD",
        400: "#70ADFC",
        500: "#3D90FB",
        600: "#2D7FE8",
        700: "#1E6ED5",
        800: "#0F5EC2",
        900: "#004DAF",
      },
      green: {
        100: "#F4FEF8",
        300: "#9ADFB7",
        500: "#40C075",
        700: "#2C8957",
        900: "#18523A",
      },
      yellow: {
        100: "#FFFDF8",
        300: "#F9E4B6",
        500: "#F3C96C",
        700: "#A78842",
        900: "#5C4818",
      },
      red: {
        50: "#FEF2F2",
        100: "#FEE2E2",
        200: "#FECACA",
        300: "#FCA5A5",
        400: "#F87171",
        500: "#EF4444",
        600: "#DC2626",
        700: "#B91C1C",
        800: "#991B1B",
        900: "#7F1D1D",
      },
      lightBlue: {
        600: "#0284C7",
      },
      indigo: {
        600: "#4F46E5",
      },
    },
    borderRadius: {
      0: "0rem",
      4: "0.25rem",
      8: "0.5rem",
      full: "9999px",
    },
    maxWidth: {
      60: "15rem",
      72: "18rem",
      96: "24rem",
      160: "40rem",
      full: "100%",
    },
    maxHeight: {
      60: "15rem",
      72: "18rem",
      96: "24rem",
      160: "40rem",
      full: "100%",
    },
  },
  plugins: [require("tailwindcss-labeled-groups")(["nested"])],
  corePlugins: {
    preflight: false,
  },
};
