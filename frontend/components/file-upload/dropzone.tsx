'use client'
import React, { useRef } from "react";
import { File } from "lucide-react";
import { Input } from "@/components/ui/input";

interface DropzoneProps {
  onFileSelect: (file: File) => void;
  filesAccepted?: string[];
}

export default function Dropzone({ onFileSelect, filesAccepted = [".yaml"] }: DropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const allowedExtensions = filesAccepted.map((ext) => ext.trim().toLowerCase());

  const isValidFileType = (fileName: string) => {
    return allowedExtensions.some((ext) => fileName.toLowerCase().endsWith(ext));
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();

    const file = e.dataTransfer.files[0];
    if (file && isValidFileType(file.name)) {
      onFileSelect(file);
    } else {
      alert(`Only files of type: ${allowedExtensions.join(", ")} are allowed`);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleClick = () => {
    inputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && isValidFileType(file.name)) {
      onFileSelect(file);
    } else {
      alert(`Only files of type: ${allowedExtensions.join(", ")} are allowed`);
    }
  };

  return (
    <div>
      {/* Drop Zone */}
      <div
        className="border-2 border-dashed border-gray-200 rounded-lg flex flex-col gap-1 p-6 items-center cursor-pointer"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={handleClick}
      >
        <File size={50} />
        <span className="text-sm font-medium text-gray-500">
          Drag and drop a file or click to browse
        </span>
        <span className="text-xs text-gray-500">
          Allowed files: {allowedExtensions.join(", ")}
        </span>
      </div>

      {/* Hidden File Input */}
      <Input
        id="file"
        ref={inputRef}
        type="file"
        accept={allowedExtensions.join(",")}
        onChange={handleFileChange}
        className="hidden"
      />
    </div>
  );
}
