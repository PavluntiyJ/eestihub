"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { MapPin } from "lucide-react";
import { AddressSearch } from "@/features/addresses/components/address-search";
import type { AddressCandidate } from "@/types/api";
import { LocationContext } from "./location-context";

export function LocationExplorer({locale}: {locale: string}) {
  const t = useTranslations("transit");
  const [address, setAddress] = useState<AddressCandidate | null>(null);

  return <section id="location" aria-labelledby="location-title" className="space-y-5 rounded-2xl border border-primary/30 bg-primary/5 p-5 sm:p-6">
    <div className="flex items-start gap-3">
      <MapPin aria-hidden="true" className="mt-1 h-6 w-6 shrink-0 text-primary" />
      <div className="space-y-2">
        <h2 id="location-title" className="font-heading text-2xl font-semibold">{t("explorerTitle")}</h2>
        <p className="text-muted-foreground">{t("explorerDescription")}</p>
      </div>
    </div>
    <AddressSearch onSelect={setAddress} />
    {address && <LocationContext key={address.id} address={address} locale={locale} />}
  </section>;
}
