library(tidyverse)
library(arrow)

exercises <- read_feather("exercices.feather")

exercises_clean <- exercises |> 
  mutate(duration = (stopTime - startTime),
         duration_min = as.integer(duration / 60))


exercises_clean |> glimpse()
