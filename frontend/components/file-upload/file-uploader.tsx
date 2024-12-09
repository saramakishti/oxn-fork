'use client'
import React, { useState } from "react";
import yaml from "js-yaml";
import { Trash, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import Dropzone from "./dropzone";
import ParsedContentDisplay from "./parsed-file";

interface FileUploaderProps {
  filesAccepted?: string[];
  handleDialogClose: () => void;
}

export default function FileUploader({ filesAccepted = [".yaml"], handleDialogClose }: FileUploaderProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [parsedContent, setParsedContent] = useState<object | null>(null);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setParsedContent(null);
  };

  const handleUpload = () => {
    if (selectedFile) {
      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const yamlContent = event.target?.result as string;
          const parsedData: any = yaml.load(yamlContent);
          setParsedContent(parsedData);
        } catch (error) {
          alert("Error parsing YAML file");
          console.error(error);
        }
      };
      reader.readAsText(selectedFile);
    } else {
      alert("Please select a file first");
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setParsedContent(null);
  };

  return (
    <div>
      <div className="p-6 space-y-4">
        {/* Show Dropzone when no file is selected */}
        {!selectedFile && (
          <Dropzone onFileSelect={handleFileSelect} filesAccepted={filesAccepted} />
        )}

        {/* Show Upload Button when a file is selected but not yet uploaded */}
        {selectedFile && !parsedContent && (
          <div>
            <div className="text-sm text-gray-700 flex items-center justify-between">
              <span>Selected file: {selectedFile.name}</span>
              <Button variant="destructive" size="sm" onClick={handleRemoveFile}>
                <Trash />
              </Button>
            </div>
            <div className="flex justify-center mt-4">
              <Button size="lg" onClick={handleUpload}>
                <Upload />
                Upload
              </Button>
            </div>
          </div>
        )}

        {/* Show Parsed Content when available */}
        {parsedContent && selectedFile && (
          <ParsedContentDisplay
            handleDialogClose={handleDialogClose}
            fileName={selectedFile.name}
            parsedContent={parsedContent}
            onRemoveFile={handleRemoveFile}
          />
        )}
      </div>
    </div>
  );
}
