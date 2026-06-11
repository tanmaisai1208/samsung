So i have run this code on multiple csv files of Soc time series data, and found the autocorr and hurst exponent values based on the dSocdt parameter and came to conclusion that for most the data files the H value is more than 0.7, and for very few files value lies between 0.5-0.6 and very rarely for very few files value is between 0.4-0.5. 

Now we can proceed to doing of actual project statment where we have to do training and prediciting of user usage patterns, phone charging and discharging patterns of future. the reseach paper based on which we took refernece had done it using SoM(Self-organizing maps) based approach. the compulsory approach which we need to follow is lets say we have 45 days of data. we take first 2 weeks(day1-14) window of data as training and take (Day 15-21) as test data/unseen data and calcualte the accuracy, then we move the training 2 week window and test unseen data ahead by 1week and do the same, we follow this until we came to end of data set and calculate all accuracies

below is the set of accuracies values acheived by them using SoM on different set of unseen days
day 1-7 : 56.1%
day 8-14 : 32.61%
day 15-21 : 57.14%
day 22-28 : 64.1%
day 29-35 : 60%
day 36-42 : 54.17%
day 43-45 : 41.18%

now we too have to follow the same thing of taking 2 week train window and 1 week ahead of unseen data, but we have to use different models/methods/approaches to increase overall accuracy to even small extent enough. So dont give codes to execute the train and test, just answer in chat here what models, methods we can use
