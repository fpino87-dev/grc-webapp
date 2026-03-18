import { useState } from "react";
import { useTranslation } from "react-i18next";

interface ModuleHelpProps {
  title: string;
  description: string;
  steps: string[];
  connections: { module: string; relation: string }[];
  configNeeded?: string[];
}

export function ModuleHelp({
  title,
  description,
  steps,
  connections,
  configNeeded,
}: ModuleHelpProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 text-xs font-bold hover:bg-blue-200 flex items-center justify-center ml-2"
        title={t("help.open_title")}
        onClick={() => setOpen(true)}
      >
        ?
      </button>

      {open && (
        <div className="fixed inset-0 z-40">
          <div
            className="absolute inset-0 bg-black/30"
            onClick={() => setOpen(false)}
          />
          <aside className="absolute top-0 right-0 h-full w-[400px] bg-white shadow-2xl z-50 flex flex-col">
            <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
              <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="w-7 h-7 flex items-center justify-center rounded-full text-gray-500 hover:bg-gray-100 hover:text-gray-800"
                aria-label={t("help.close_aria")}
              >
                ×
              </button>
            </header>

            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 text-sm">
              <section>
                <h4 className="text-xs font-semibold tracking-wide text-gray-500 uppercase mb-1">
                  {t("help.sections.what_is")}
                </h4>
                <p className="text-gray-700 whitespace-pre-line">{description}</p>
              </section>

              {steps.length > 0 && (
                <section>
                  <h4 className="text-xs font-semibold tracking-wide text-gray-500 uppercase mb-1">
                    {t("help.sections.how_to")}
                  </h4>
                  <ol className="list-decimal list-inside space-y-1 text-gray-700">
                    {steps.map((step, idx) => (
                      <li key={idx}>{step}</li>
                    ))}
                  </ol>
                </section>
              )}

              {connections.length > 0 && (
                <section>
                  <h4 className="text-xs font-semibold tracking-wide text-gray-500 uppercase mb-1">
                    {t("help.sections.connected_to")}
                  </h4>
                  <ul className="space-y-1">
                    {connections.map((c, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-gray-700">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 text-xs font-medium">
                          {c.module}
                        </span>
                        <span className="text-xs text-gray-600">{c.relation}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {configNeeded && configNeeded.length > 0 && (
                <section>
                  <h4 className="text-xs font-semibold tracking-wide text-gray-500 uppercase mb-1">
                    {t("help.sections.before_start")}
                  </h4>
                  <ul className="list-disc list-inside space-y-1 text-gray-700 text-xs">
                    {configNeeded.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </section>
              )}
            </div>
          </aside>
        </div>
      )}
    </>
  );
}

