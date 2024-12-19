'use client'
import React from "react";
import { Cable, Save, Trash } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Button } from "../ui/button";
import { toast } from "react-toastify";
import { useApi } from "@/hooks/use-api";

interface ParsedContentDisplayProps {
  fileName: string;
  parsedContent: object;
  onRemoveFile: () => void;
  handleDialogClose: () => void;
  disableStartButton: () => void;
}

export default function ParsedContentDisplay({
  fileName,
  parsedContent,
  onRemoveFile,
  handleDialogClose,
  disableStartButton,
}: ParsedContentDisplayProps) {

  const [isSavedFile, setIsSavedFile] = React.useState(false)
  const [experimentId, setExperimentId] = React.useState<string | null>(null);

  const [createExperimentResponse, setCreateExperimentResponse] = React.useState<any>(null);
  const [startExperimentResponse, setStartExperimentResponse] = React.useState<any>(null);

  const { get, post, loading, error } = useApi();

  const onCreateExperiment = async () => {
    try {
      // TODO: Uncomment API call and remove hardcoded response below
      const response = await post("/experiments", { name: "experiment.yaml", config: parsedContent });
     
      setCreateExperimentResponse(response)
      console.log("File saved response:", response);
      toast.success('File saved successfully!');
      // if (response) {
        // setExperimentId(response.id)
      // }
    } catch (error) {
      toast.error('An error occurred. Please try again!');
      console.error("Error creating experiment file:", error);
    }
  };

  const onStartExperiment = async () => {
    try {
      // TODO: Uncomment API call and remove hardcoded response below
      const response = await post(`/experiments/${experimentId}run`, {
        runs: 1,
        output_format: "json"
      });
      setStartExperimentResponse(response)
      console.log("Experiment started running:", response);
      toast.success('Experiment started successfully!');
    } catch (error) {
      toast.error('An error occurred. Please try again!');
      console.error("Error starting experiment:", error);
    }
  }

  const handleFileSave = () => {
    setIsSavedFile(true);
    onCreateExperiment();
  }

  const handleStartExperiment = () => {
    if (experimentId) {
      onStartExperiment();
      disableStartButton();
      handleDialogClose();
    }
  }

  return (
    <div>
      <div className="text-sm text-gray-700 flex items-center justify-between">
        <span>Selected file: {fileName}</span>
        <Button variant="destructive" size="sm" onClick={onRemoveFile}>
          <Trash />
        </Button>
      </div>

      <div className="mt-4">
        <h3 className="text-lg font-semibold mb-2">File Preview:</h3>
        <div className="max-h-[40vh] max-w-full overflow-auto">
          <SyntaxHighlighter
            language="json"
            style={oneDark}
            wrapLines={true}
            customStyle={{ whiteSpace: "pre" }}
          >
            {JSON.stringify(parsedContent, null, 2)}
          </SyntaxHighlighter>
        </div>
      </div>

      <div className="flex justify-end gap-2 my-2 w-full">
        <Button disabled={isSavedFile} onClick={handleFileSave} variant="outline">
          <Save />
          {isSavedFile ? 'File saved!' : 'Save file'}
        </Button>

        <Button disabled={!isSavedFile} onClick={handleStartExperiment}>
          <Cable />
          Start
        </Button>
      </div>
    </div>
  );
}
