"use client";

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import type { DistrictRent } from "@/types/api";

type RentBarChartProps = {
  districts: DistrictRent[];
  label: string;
};

export function RentBarChart({ districts, label }: RentBarChartProps) {
  const chartConfig = {
    avg_rent_2room: {
      label,
      color: "var(--chart-2)",
    },
  } satisfies ChartConfig;

  return (
    <ChartContainer config={chartConfig} className="min-h-[320px] w-full">
      <BarChart accessibilityLayer data={districts} margin={{ left: 4, right: 4 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="name"
          tickLine={false}
          tickMargin={10}
          axisLine={false}
          interval={0}
          angle={-25}
          textAnchor="end"
          height={72}
        />
        <YAxis tickLine={false} axisLine={false} tickMargin={8} width={48} />
        <ChartTooltip
          cursor={false}
          content={<ChartTooltipContent hideLabel nameKey="avg_rent_2room" />}
        />
        <Bar
          dataKey="avg_rent_2room"
          name={label}
          fill="var(--color-avg_rent_2room)"
          radius={[8, 8, 0, 0]}
        />
      </BarChart>
    </ChartContainer>
  );
}
