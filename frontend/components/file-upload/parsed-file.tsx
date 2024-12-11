'use client'
import React from "react";
import { Cable, Save, Trash } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Button } from "../ui/button";
import axios from "axios";

interface ParsedContentDisplayProps {
  fileName: string;
  parsedContent: object;
  onRemoveFile: () => void;
  handleDialogClose: () => void;
}

export default function ParsedContentDisplay({
  fileName,
  parsedContent,
  onRemoveFile,
  handleDialogClose,
}: ParsedContentDisplayProps) {

  const [isSavedFile, setIsSavedFile] = React.useState(false)
  const [experimentId, setExperimentId] = React.useState(null);


  const handleFileSave = async () => {
    try {
      const response = await axios({
        method: 'post',
        url: 'http://localhost:8000/experiments',
        data: {
          name: 'testexperiment',
          config: parsedContent
        }
      });
      
      if (response.status === 200) {
        setIsSavedFile(true);
        setExperimentId(response.data.id);
        console.log("Backend response.data with 200 ok : ", response.data)  
      }
    } catch (error) {
      console.error('Error during experiment save operation:', error);
      // Optional: Add error state or show error message to user
    }
  }

  const handleStartExperiment = () => {
    alert('Experiment is starting...')
    handleDialogClose();
     if(experimentId){
       axios({
         method: 'post',
         url: `http://localhost:8000/experiments/${experimentId}/runsync`,
       });
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
