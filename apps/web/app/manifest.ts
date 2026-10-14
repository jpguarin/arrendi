import type { MetadataRoute } from "next";

import { appIcons } from "@/lib/environment";
import { BACKGROUND_LIGHT } from "@/lib/theme";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Arrendi",
    short_name: "Arrendi",
    description: "Genera tus cuentas de cobro cada mes, envíalas por correo y sabe quién te debe.",
    lang: "es-CO",
    start_url: "/",
    display: "standalone",
    background_color: BACKGROUND_LIGHT,
    theme_color: BACKGROUND_LIGHT,
    icons: [
      { src: appIcons.small, sizes: "192x192", type: "image/png" },
      { src: appIcons.large, sizes: "512x512", type: "image/png" },
      { src: appIcons.large, sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
