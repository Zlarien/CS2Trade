"use client";

import { type FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { steamLoginUrl } from "../lib/api";

export default function HomePage() {
  const [identifier, setIdentifier] = useState("");
  const router = useRouter();

  function handleManualImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = identifier.trim();
    if (!trimmed) return;
    router.push(`/inventory?identifier=${encodeURIComponent(trimmed)}`);
  }

  return (
    <main>
      <h1>CS2Trade</h1>
      <p>
        Analyse ton inventaire CS2 et recommande, item par item, de garder, vendre ou faire un
        trade-up contract, pour faire croitre la valeur totale de l&apos;inventaire. Calcul
        deterministe, base sur les prix marche actuels.
      </p>

      <section>
        <h2>Connexion Steam</h2>
        <p>
          Synchronisation continue de ton inventaire. Tu peux exclure les items que
          l&apos;outil ne doit jamais toucher.
        </p>
        <a href={steamLoginUrl()}>Se connecter avec Steam</a>
      </section>

      <section>
        <h2>Import manuel</h2>
        <p>
          Sans lier ton compte : ton inventaire doit etre temporairement public le temps de
          l&apos;import.
        </p>
        <form onSubmit={handleManualImport}>
          <input
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
            placeholder="SteamID64, URL de profil, ou vanity name"
            aria-label="SteamID64 ou URL de profil"
          />
          <button type="submit">Analyser</button>
        </form>
      </section>
    </main>
  );
}
