import { useEffect, useState } from "react";

interface Props {
  deadlineISO: string;
  label: string;
  urgentMinutes?: number;
}

export function CountdownTimer({ deadlineISO, label, urgentMinutes = 120 }: Props) {
  const [remaining, setRemaining] = useState(0);

  useEffect(() => {
    const calc = () =>
      setRemaining(Math.max(0, new Date(deadlineISO).getTime() - Date.now()));
    calc();
    const id = setInterval(calc, 1000);
    return () => clearInterval(id);
  }, [deadlineISO]);

  if (remaining === 0)
    return <span className="text-red-600 font-bold">SCADUTO — {label}</span>;

  const totalMinutes = remaining / 60000;
  const color =
    totalMinutes < 30
      ? "text-red-600"
      : totalMinutes < urgentMinutes
      ? "text-orange-500"
      : "text-green-600";

  const d = Math.floor(remaining / 86400000);
  const h = Math.floor((remaining % 86400000) / 3600000);
  const m = Math.floor((remaining % 3600000) / 60000);
  const s = Math.floor((remaining % 60000) / 1000);
  const fmt = `${d > 0 ? d + "g " : ""}${String(h).padStart(2, "0")}:${String(
    m
  ).padStart(2, "0")}:${String(s).padStart(2, "0")}`;

  return (
    <span className={`font-mono font-semibold ${color}`}>
      {label}: {fmt}
    </span>
  );
}

