import type { DistrictRent } from "@/types/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type RentTableLabels = {
  district: string;
  oneRoom: string;
  twoRoom: string;
  threeRoom: string;
  utilities: string;
};

type RentTableProps = {
  districts: DistrictRent[];
  labels: RentTableLabels;
  formatCurrency: (value: number) => string;
};

export function RentTable({ districts, labels, formatCurrency }: RentTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{labels.district}</TableHead>
          <TableHead className="text-right">{labels.oneRoom}</TableHead>
          <TableHead className="text-right">{labels.twoRoom}</TableHead>
          <TableHead className="text-right">{labels.threeRoom}</TableHead>
          <TableHead className="text-right">{labels.utilities}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {districts.map((district) => (
          <TableRow key={district.name}>
            <TableCell className="font-medium">{district.name}</TableCell>
            <TableCell className="text-right tabular-nums">
              {formatCurrency(district.avg_rent_1room)}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {formatCurrency(district.avg_rent_2room)}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {formatCurrency(district.avg_rent_3room)}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {formatCurrency(district.avg_utilities)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
