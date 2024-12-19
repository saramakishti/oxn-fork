"use client";
import React, { useEffect, useState } from "react";
import { ExperimentsTable } from "../dynamic-table/table";
import { allExperimentsConfig } from "../dynamic-table/table-columns";
import { useApi } from "@/hooks/use-api";

export default function ExperimentsView() {
  const [experiments, setExperiments] = useState<any[]>([]);

  const { get, loading } = useApi();

  const fetchExperiments = async () => {
    try {
      const response = await get("/experiments");
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
