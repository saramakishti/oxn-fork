'use client'
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Cable } from "lucide-react";
import FileUploader from "../file-upload/file-uploader";

export default function StartExperimentDialog() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="default">
          <Cable />
          Start new experiment
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[900px] w-full max-h-[90vh] overflow-auto">
        <DialogHeader>
          <DialogTitle>Start new experiment</DialogTitle>
          <DialogDescription>
            Upload a YAML file with experiment configurations.
          </DialogDescription>
        </DialogHeader>
        {/* File Upload Process */}
        <FileUploader />
      </DialogContent>
    </Dialog>
  );
}
