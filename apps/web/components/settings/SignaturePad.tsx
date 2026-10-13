"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";

type SignaturePadProps = {
  /** While the signature goes up: the pad stays as it is and takes no more strokes. */
  saving: boolean;
  onCancel: () => void;
  /** The signature as a PNG with nothing behind the strokes. */
  onDone: (file: File) => void;
};

const STROKE_WIDTH = 2.5;

/** A sheet to sign on, with a finger or the mouse. */
export function SignaturePad({ saving, onCancel, onDone }: SignaturePadProps) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);
  const [empty, setEmpty] = useState(true);

  // The exporting of a tap already on its way: a second tap must not send it twice.
  const exporting = useRef(false);

  // As many pixels as the screen really has, so the strokes are sharp on the bill. Sized
  // again whenever the sheet changes size, as when the phone is turned: its pixels have
  // to match what the finger touches. That wipes the sheet, which is said below.
  useEffect(() => {
    const sheet = canvas.current;
    if (!sheet) return;
    const fit = () => {
      const scale = window.devicePixelRatio || 1;
      const width = Math.round(sheet.clientWidth * scale);
      const height = Math.round(sheet.clientHeight * scale);
      if (sheet.width === width && sheet.height === height) return;
      sheet.width = width;
      sheet.height = height;
      const pen = sheet.getContext("2d");
      if (!pen) return;
      pen.scale(scale, scale);
      pen.lineWidth = STROKE_WIDTH;
      pen.lineCap = "round";
      pen.lineJoin = "round";
      // The ink of the theme, which is the same in the light and the dark one.
      pen.strokeStyle = getComputedStyle(sheet).color;
      drawing.current = false;
      setEmpty(true);
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(sheet);
    return () => observer.disconnect();
  }, []);

  function point(event: React.PointerEvent<HTMLCanvasElement>) {
    const box = event.currentTarget.getBoundingClientRect();
    return [event.clientX - box.left, event.clientY - box.top] as const;
  }

  function start(event: React.PointerEvent<HTMLCanvasElement>) {
    const pen = canvas.current?.getContext("2d");
    if (!pen || saving) return;
    // The stroke goes on even if the finger leaves the sheet.
    event.currentTarget.setPointerCapture(event.pointerId);
    drawing.current = true;
    const [x, y] = point(event);
    pen.beginPath();
    pen.moveTo(x, y);
    // A tap leaves a dot.
    pen.lineTo(x + 0.1, y + 0.1);
    pen.stroke();
    setEmpty(false);
  }

  function move(event: React.PointerEvent<HTMLCanvasElement>) {
    const pen = canvas.current?.getContext("2d");
    if (!pen || !drawing.current) return;
    pen.lineTo(...point(event));
    pen.stroke();
  }

  function clear() {
    const sheet = canvas.current;
    sheet?.getContext("2d")?.clearRect(0, 0, sheet.width, sheet.height);
    setEmpty(true);
  }

  function done() {
    if (exporting.current) return;
    exporting.current = true;
    canvas.current?.toBlob((blob) => {
      exporting.current = false;
      if (blob) onDone(new File([blob], "firma.png", { type: "image/png" }));
    }, "image/png");
  }

  return (
    <div className="flex flex-col gap-2">
      <canvas
        ref={canvas}
        role="img"
        aria-label="Hoja para dibujar tu firma"
        // `touch-none`: a finger on the sheet signs, it does not scroll the page.
        className="h-44 w-full touch-none rounded-xl border border-border-dashed bg-paper text-ink"
        onPointerDown={start}
        onPointerMove={move}
        onPointerUp={() => (drawing.current = false)}
        onPointerCancel={() => (drawing.current = false)}
      />
      <p className="text-support text-muted-foreground">
        Firma con el dedo dentro del recuadro, como lo harías en papel. Si giras el celular, el
        recuadro se borra.
      </p>
      <div className="grid grid-cols-3 gap-2">
        <Button type="button" variant="outline" size="md" disabled={saving} onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="button" variant="outline" size="md" disabled={empty || saving} onClick={clear}>
          Borrar
        </Button>
        <Button type="button" size="md" disabled={empty || saving} onClick={done}>
          {saving ? "Guardando…" : "Usar firma"}
        </Button>
      </div>
    </div>
  );
}
