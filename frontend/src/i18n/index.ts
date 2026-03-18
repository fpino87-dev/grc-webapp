import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import it_common from "./it/common.json";
import en_common from "./en/common.json";
import fr_common from "./fr/common.json";
import pl_common from "./pl/common.json";
import tr_common from "./tr/common.json";

i18n.use(initReactI18next).init({
  resources: {
    it: { common: it_common },
    en: { common: en_common },
    fr: { common: fr_common },
    pl: { common: pl_common },
    tr: { common: tr_common },
  },
  lng: localStorage.getItem("grc_lang") || "it",
  fallbackLng: "en",
  defaultNS: "common",
  interpolation: { escapeValue: false },
});

export default i18n;

