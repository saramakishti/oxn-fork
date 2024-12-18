"use client";
import React, { useEffect, useState } from "react";
import { ExperimentsTable } from "../dynamic-table/table";
import { allExperimentsConfig } from "../dynamic-table/table-columns";
import { useApi } from "@/hooks/use-api";
// import { useApi } from "@/hooks/use-api";

export default function ExperimentsView() {
  const [experiments, setExperiments] = useState<any[]>([]);

  const {get, loading} = useApi();

  // Fetch Experiments
  const fetchExperiments = async () => {
    try {
      // TODO: Uncomment API call and remove hardcoded response below
      // const response = await get("/experiments");
      const response = [
        {
          "id": "01733873826",
          "name": "string",
          "status": "PENDING",
          "started_at": null,
          "completed_at": null,
          "error_message": null
        },
        {
          "id": "11733874120",
          "name": "string",
          "status": "PENDING",
          "started_at": null,
          "completed_at": null,
          "error_message": null
        }
      ]
      console.log('Fetching experiments...', response)
      setExperiments(response);
    } catch (error) {
      console.error("Error fetching experiments:", error);
    }
  };


  useEffect(() => {
    fetchExperiments();
  }, []);

  return <ExperimentsTable filterColumnKey="id" data={experiments} columns={allExperimentsConfig} />
}
