'use client'
import React from "react";
import { Cable, Save, Trash } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Button } from "../ui/button";

interface ParsedContentDisplayProps {
  fileName: string;
  parsedContent: object;
  onRemoveFile: () => void;
}

export default function ParsedContentDisplay({
  fileName,
  parsedContent,
  onRemoveFile,
}: ParsedContentDisplayProps) {

  const [isSavedFile, setIsSavedFile] = React.useState(false)

  const handleFileSave = () => {
    //TODO: Add API to save file in the backend
    setIsSavedFile(true);
  }

  const handleStartExperiment = () => {
    //TODO: Add API to start experiment
    alert('Experiment is starting...')
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

      <div className="flex justify-between my-2">
        <Button disabled={isSavedFile} onClick={handleFileSave} variant="outline">
          <Save />
          {isSavedFile ? 'File saved!' : 'Save file'}
        </Button>

        <Button onClick={handleStartExperiment}>
          <Cable />
          Start
        </Button>
      </div>
    </div>
  );
}
