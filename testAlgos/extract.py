import json
import os



# Read and parse the JSON file
with open('./testAlgos/data/recommendationService.json', "r") as file:
    json_data = json.load(file)

# Print the imported data
#print(json_data)
data = json_data['data']
for span in data[0]['spans']:
     span_kind_value = None
     for obj in span['tags']:
          if obj["key"] == "span.kind":
               span_kind_value = obj["value"]
               print(span_kind_value)
               break  # Exit the loop when found

#span_kind_value = next(item['value'] for item in json_data if item['key'] == "span.kind")