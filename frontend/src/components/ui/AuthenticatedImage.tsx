import { useEffect, useState } from "react";
import { apiClient } from "../../api/client";

interface Props {
  src: string;
  alt: string;
  className?: string;
}

/**
 * Carica un'immagine tramite apiClient (con JWT Authorization header)
 * e la mostra come blob URL. Necessario per endpoint API interni protetti
 * da auth che non possono ricevere token via tag <img>.
 * Per URL esterni (http/https) usa un <img> normale senza JWT.
 */
export function AuthenticatedImage({ src, alt, className }: Props) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);

  const isExternal = src.startsWith("http://") || src.startsWith("https://");

  useEffect(() => {
    if (!src || isExternal) return;
    let objectUrl: string | null = null;
    let cancelled = false;

    apiClient
      .get(src, { responseType: "blob", baseURL: "" })
      .then((res) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(res.data);
        setBlobUrl(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setBlobUrl(null);
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [src, isExternal]);

  if (!src) return null;
  if (isExternal) return <img src={src} alt={alt} className={className} />;
  if (!blobUrl) return null;
  return <img src={blobUrl} alt={alt} className={className} />;
}
