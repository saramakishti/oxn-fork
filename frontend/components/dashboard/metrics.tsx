'use client'
import React from "react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { cardConfiguration } from "@/configurations/metrics";


const Metrics = () => {

  return (
    <div>
      <div className="grid grid-cols-4 gap-4">
        {cardConfiguration.map((card, index) => {
          return (
            <Card key={index}>
              <CardHeader>
                <div className="flex items-center space-x-2">
                  {card.icon}
                  <CardTitle>{card.title}</CardTitle>
                </div>
                <CardDescription>{card.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <p>Value here</p> {/* Replace with actual metrics */}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  )
}

export default Metrics;