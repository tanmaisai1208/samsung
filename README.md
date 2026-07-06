So the way u train the model doesn't change, u have to train based on the whole data (don't clip neither of positive or negative), 
but the target variabke or thing whihc u predict changes actually, now u have to predict the charging events or the time when a particular user 
does his charging in each test day. and by charging doesnt mean just slight increase in SOC and then falling down etc, some significant big or medium increase in 
SOC will be considered as charging . because our use-case on which we are focsuing now is, suggesting charging schedules to user. 

And the metric to decide how good the model is MAE, so do the MAE between actual charging schedule time done by user and the time which model predcited as charging schedule.
like lets say there is a charging scedhule event or peak in time-series of SOC done by user at 3pm and model predicts it as 4pm, so ur error for this data point is 1hr etc
