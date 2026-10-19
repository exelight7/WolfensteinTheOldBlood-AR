/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        arabic: ['"IBM Plex Sans Arabic"', '"Segoe UI"', "Tahoma", "sans-serif"],
      },
      colors: {
        ink: { 950: "#08090c", 900: "#0c0e13", 850: "#11141b", 800: "#171b24", 700: "#232936" },
        ember: { 400: "#e8a33d", 500: "#d98a1f", 600: "#b96f12" },
      },
      keyframes: {
        rise: { "0%": { opacity: "0", transform: "translateY(10px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        pulseSoft: { "0%,100%": { opacity: "1" }, "50%": { opacity: ".55" } },
      },
      animation: { rise: "rise .45s cubic-bezier(.22,1,.36,1) both", pulseSoft: "pulseSoft 2s ease-in-out infinite" },
    },
  },
  plugins: [],
};
