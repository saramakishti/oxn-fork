"use client";
import { Download, RefreshCcw } from "lucide-react";
import { Button } from "../ui/button";
import { toast } from "react-toastify";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useApi } from "@/hooks/use-api";

export default function ExperimentTableActions({ experimentID }: { experimentID: string }) {

  const { get } = useApi();

  const onRefreshStatus = async () => {
    try {
      const response = await get(`/experiments/${experimentID}/status`);
      console.log(response);
    } catch (error) {
      console.error('Error refreshing status...', error)
      toast.error("Error happened while refreshing status of experiment.");
    }
  }

  const onDownloadBenchmark = async () => {
    try {
      const response = await get(`/experiments/${experimentID}/benchmark`);
      console.log(response);
    } catch (error) {
      console.error('Error downloading benchmark...', error)
      toast.error("Error happened while downloading file.");
    }
  }

  return (
    <div>

      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="sm" onClick={onRefreshStatus}>
              <RefreshCcw />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>Refresh experiment status</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>


      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="sm" onClick={onDownloadBenchmark}>
              <Download />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>Download benchmark file</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div >
  )
}

