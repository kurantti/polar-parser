library(tidyverse)
library(jsonlite)
library(furrr)

fileList <-  dir("./data/", pattern = "training-session-.+json", full.names = T) |> 
    as.list()
    
filesreadJson <- fileList |> future_map(\(x) fromJSON(x))

df <- filesreadJson |> enframe()

parsed <- df |> 
  hoist(value, "startTime", "stopTime","distance", "averageHeartRate", 
        sport = list("exercises", "sport"),
        ascent = list("exercises", "ascent"),
        descent = list("exercises", "descent")
        )

cleaned <- parsed |> select(-value) |> type_convert()
cleaned

library(arrow)
cleaned |> 
  write_feather("exercices.feather")


