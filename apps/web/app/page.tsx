import { ThemeSelector } from "@/components/ThemeSelector";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

// Provisional: shows the base components until the sign-in screens replace it.
export default function HomePage() {
  return (
    <main className="flex flex-1 flex-col gap-5 px-5 py-8">
      <div className="flex flex-col gap-1">
        <h1 className="text-title font-bold">Arrendi</h1>
        <p className="text-support text-muted-foreground">Estamos construyendo la aplicación.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Componentes base</CardTitle>
          <CardDescription>Así se ven los botones y los campos.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="sample-email">Correo</Label>
            <Input id="sample-email" type="email" placeholder="tu@correo.com" />
          </div>
          <Button className="w-full">Continuar</Button>
          <Button variant="outline" size="md" className="w-full">
            Continuar con Google
          </Button>
          <Button variant="dashed" size="md" className="w-full">
            Agregar unidad
          </Button>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm">
              Cambiar
            </Button>
            <Button variant="destructive" size="sm">
              Anular
            </Button>
          </div>
        </CardContent>
      </Card>

      <section className="flex flex-col gap-2">
        <h2 className="text-section font-semibold">Apariencia</h2>
        <ThemeSelector />
      </section>
    </main>
  );
}
