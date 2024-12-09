"use client"

import Link from "next/link";
import { ArrowUpDown, Copy, Download, Eye, MoreHorizontal } from "lucide-react";
import { ColumnDef } from "@tanstack/react-table"
import { ExperimentType } from "@/types"
import { formatDate } from "@/utils/dates";
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger, DropdownMenuLabel, DropdownMenuItem, DropdownMenuSeparator } from "../ui/dropdown-menu";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";


export const allResultsConfig: ColumnDef<ExperimentType>[] = [
  {
    accessorKey: "experimentDate",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Date
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      )
    },
    cell: ({ row }: any) => formatDate(row.original.experimentDate)
  },
  {
    accessorKey: "experimentId",
    header: "Experiment ID",
  },
  {
    accessorKey: "numberOfRuns",
    header: "# of Runs",
  },
  {
    accessorKey: "treatmentNames",
    header: "Treatment Names",
    cell: ({ row }: any) => {

      return (
        row.original.treatmentNames.map((name: string) => {
          return (
            <Badge className="mx-1" variant="outline">{name}</Badge>
          )
        })
      )
    }
  },
  {
    accessorKey: "treatmentTypes",
    header: "Treatment Types",
    cell: ({ row }: any) => {
      return (
        row.original.treatmentTypes.map((type: string) => {
          return (
            <Badge className="mx-1" variant="secondary">{type}</Badge>
          )
        })
      )
    }
  },
  {
    id: "actions",
    header: "Actions",
    cell: ({ row }: any) => {
      const experimentId = row.original.experimentId;

      return (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0">
              <span className="sr-only">Open menu</span>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">

            <DropdownMenuItem
              className="cursor-pointer"
              onClick={() => navigator.clipboard.writeText(row.experimentId)}
            >
              <Copy />
              Copy experiment ID
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="cursor-pointer">
              <Eye />
              <Link href={`/results/${experimentId}`}>View details</Link>
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Button>
                {/* TODO: Add API to download file */}
                <Download />
                Download file
              </Button>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
    },
  },
];

export const resultDetailsConfig: ColumnDef<any>[] = [
  // {
  //   accessorKey: 'experimentId',
  //   header: 'Experiment ID',
  // },
  // {
  //   accessorKey: 'experimentDate',
  //   header: 'Experiment Date',
  //   cell: ({ row }) => formatDate(row.original.experimentDate),
  // },
  {
    accessorKey: 'runDate',
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Date
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      )
    },
    cell: ({ row }) => formatDate(row.original.runDate),
  },
  {
    accessorKey: 'runId',
    header: 'Run ID',
  },
  {
    accessorKey: 'interactionId',
    header: 'Interaction ID',
  },
  {
    accessorKey: "treatmentName",
    header: "Treatment Name",
    cell: ({ row }: any) => {
      return <Badge className="mx-1" variant="outline">{row.original.treatmentName}</Badge>
    }
  },
  {
    accessorKey: "treatmentType",
    header: "Treatment Type",
    cell: ({ row }: any) => {
      return <Badge className="mx-1" variant="secondary">{row.original.treatmentType}</Badge>
    }
  },
  {
    accessorKey: 'treatmentStart',
    header: 'Treatment Start',
    cell: ({ row }) => formatDate(row.original.treatmentStart),
  },
  {
    accessorKey: 'treatmentEnd',
    header: 'Treatment End',
    cell: ({ row }) => formatDate(row.original.treatmentEnd),
  },
  {
    accessorKey: 'responseName',
    header: 'Response Name',
  },
  {
    accessorKey: 'responseType',
    header: 'Response Type',
  },
  // {
  //   accessorKey: 'loadgenStartTime',
  //   header: 'Loadgen Start Time',
  //   cell: ({ row }) => formatDate(row.original.loadgenStartTime),
  // },
  // {
  //   accessorKey: 'loadgenEndTime',
  //   header: 'Loadgen End Time',
  //   cell: ({ row }) => formatDate(row.original.loadgenEndTime),
  // },
  {
    accessorKey: 'loadgenTotalRequests',
    header: 'Total Requests',
  },
  {
    accessorKey: 'loadgenTotalFailures',
    header: 'Total Failures',
  },
];