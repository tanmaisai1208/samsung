=================================================================
Device : 6629d47f285139f95d148293c9b8f7115840bf21970299ddf50db544d09f724d
=================================================================
  Predicting 56 days...
  Day  41/56 | 2024-07-02 | actual_events=1 pred_events=1 matched=1
  Day  51/56 | 2024-07-12 | actual_events=0 pred_events=0 matched=0
  Day  56/56 | 2024-07-17 | actual_events=0 pred_events=1 matched=0

  Predictions CSV  →  results/xgboost/charging_schedule\charging_schedule_predictions_6629d47f285139f95d148293c9b8f7115840bf21970299ddf50db544d09f724d.csv
  Saved: results/xgboost/charging_schedule\charging_schedule_sample_days_6629d47f285139f95d148293c9b8f7115840bf21970299ddf50db544d09f724d.png

  MAE (hours)              : 7.927
  True Positives (TP)      : 6
  False Positives (FP)     : 15
  False Negatives (FN)     : 3
  Event count match rate   : 33.3%

=================================================================
Device : 941a15e6d02a161f780d24d99b5c96ac7b73ed02652b95818e73473ba8d8fb66
=================================================================
  Predicting 57 days...
  Day   1/57 | 2024-05-22 | actual_events=1 pred_events=2 matched=1
  Day  57/57 | 2024-07-17 | actual_events=0 pred_events=1 matched=0

  Predictions CSV  →  results/xgboost/charging_schedule\charging_schedule_predictions_941a15e6d02a161f780d24d99b5c96ac7b73ed02652b95818e73473ba8d8fb66.csv
  Saved: results/xgboost/charging_schedule\charging_schedule_sample_days_941a15e6d02a161f780d24d99b5c96ac7b73ed02652b95818e73473ba8d8fb66.png

  MAE (hours)              : 7.375
  True Positives (TP)      : 8
  False Positives (FP)     : 6
  False Negatives (FN)     : 1
  Event count match rate   : 33.3%

=================================================================
Device : ea1f79f3b9f2510c229de2d4ee98441c7fcf39bf384b32a2212535325fb5ac69
=================================================================
  Predicting 55 days...
  Day   1/55 | 2024-05-23 | actual_events=0 pred_events=2 matched=0
  Day  11/55 | 2024-06-02 | actual_events=0 pred_events=0 matched=0
  Day  41/55 | 2024-07-02 | actual_events=0 pred_events=1 matched=0
  Day  51/55 | 2024-07-12 | actual_events=1 pred_events=0 matched=0
  Day  55/55 | 2024-07-16 | actual_events=1 pred_events=1 matched=1

  Predictions CSV  →  results/xgboost/charging_schedule\charging_schedule_predictions_ea1f79f3b9f2510c229de2d4ee98441c7fcf39bf384b32a2212535325fb5ac69.csv
  Saved: results/xgboost/charging_schedule\charging_schedule_sample_days_ea1f79f3b9f2510c229de2d4ee98441c7fcf39bf384b32a2212535325fb5ac69.png

  MAE (hours)              : 10.000
  True Positives (TP)      : 7
  False Positives (FP)     : 30
  False Negatives (FN)     : 3
  Event count match rate   : 41.0%

=================================================================
Device : ec92f70a957b2292031f4342096c17736c6d1b92a0371095875c51296e708d43
=================================================================
  Predicting 60 days...
  Day   1/60 | 2024-05-19 | actual_events=1 pred_events=0 matched=0
  Day  11/60 | 2024-05-29 | actual_events=1 pred_events=1 matched=1
  Day  21/60 | 2024-06-08 | actual_events=0 pred_events=0 matched=0
  Day  51/60 | 2024-07-08 | actual_events=0 pred_events=1 matched=0
  Day  60/60 | 2024-07-17 | actual_events=0 pred_events=0 matched=0

  Predictions CSV  →  results/xgboost/charging_schedule\charging_schedule_predictions_ec92f70a957b2292031f4342096c17736c6d1b92a0371095875c51296e708d43.csv
  Saved: results/xgboost/charging_schedule\charging_schedule_sample_days_ec92f70a957b2292031f4342096c17736c6d1b92a0371095875c51296e708d43.png

  MAE (hours)              : 4.761
  True Positives (TP)      : 18
  False Positives (FP)     : 28
  False Negatives (FN)     : 9
  Event count match rate   : 31.7%

=================================================================
Device : f44d16fb80f7e7c786028b14e831619bdc3e362c36f60f1a5f124fbace89616a
=================================================================
  Predicting 59 days...
  Day   1/59 | 2024-05-20 | actual_events=1 pred_events=1 matched=1
  Day  11/59 | 2024-05-30 | actual_events=2 pred_events=1 matched=1
  Day  21/59 | 2024-06-09 | actual_events=0 pred_events=3 matched=0

  Predictions CSV  →  results/xgboost/charging_schedule\charging_schedule_predictions_f44d16fb80f7e7c786028b14e831619bdc3e362c36f60f1a5f124fbace89616a.csv
  Saved: results/xgboost/charging_schedule\charging_schedule_sample_days_f44d16fb80f7e7c786028b14e831619bdc3e362c36f60f1a5f124fbace89616a.png

  MAE (hours)              : 4.067
  True Positives (TP)      : 15
  False Positives (FP)     : 16
  False Negatives (FN)     : 1
  Event count match rate   : 36.8%


Global summary  →  results/xgboost/charging_schedule\charging_schedule_summary.csv
  Saved: results/xgboost/charging_schedule\charging_schedule_mae_plot.png
  Saved: results/xgboost/charging_schedule\charging_schedule_tp_fp_plot.png
  Saved: results/xgboost/charging_schedule\charging_schedule_error_distribution.png

=================================================================
CHARGING SCHEDULE PREDICTION — FINAL SUMMARY
=================================================================
  3370f23cd7055a73bca859557669d8269438d7e42469389e5f315f4d225397eb  MAE=  3.95 hrs  TP=  21  FP=  47  FN=   2  EventCountMatch=24.3%
  401f02de69f658de9e87b74fd3155aa7295cc8a2fcb67d43988d051cb0c48767  MAE=  4.27 hrs  TP=   8  FP=  12  FN=   3  EventCountMatch=25.0%
  42f0e81125403519ed71e035d0c54a22fceea95362363151936ee87628c7a08e  MAE=  4.10 hrs  TP=  14  FP=  22  FN=  18  EventCountMatch=25.0%
  6629d47f285139f95d148293c9b8f7115840bf21970299ddf50db544d09f724d  MAE=  7.93 hrs  TP=   6  FP=  15  FN=   3  EventCountMatch=33.3%
  941a15e6d02a161f780d24d99b5c96ac7b73ed02652b95818e73473ba8d8fb66  MAE=  7.38 hrs  TP=   8  FP=   6  FN=   1  EventCountMatch=33.3%
  ea1f79f3b9f2510c229de2d4ee98441c7fcf39bf384b32a2212535325fb5ac69  MAE= 10.00 hrs  TP=   7  FP=  30  FN=   3  EventCountMatch=41.0%
  ec92f70a957b2292031f4342096c17736c6d1b92a0371095875c51296e708d43  MAE=  4.76 hrs  TP=  18  FP=  28  FN=   9  EventCountMatch=31.7%
  f44d16fb80f7e7c786028b14e831619bdc3e362c36f60f1a5f124fbace89616a  MAE=  4.07 hrs  TP=  15  FP=  16  FN=   1  EventCountMatch=36.8%
  OVERALL_MEAN                         MAE=  5.81 hrs  TP=  97  FP= 176  FN=  40  EventCountMatch=31.3%
