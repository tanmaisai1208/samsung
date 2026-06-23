PS C:\Users\chennagiri.s\Desktop\Soc> python xgboost_shap_analysis.py
=================================================================
SHAP ANALYSIS
=================================================================

  Loading: 006f690ab4e08bc4ba33cf30881b6d90e8045fb52a86f8e3a953b2e62ba6030e_wide.csv
  Loading: 0b2ab3916c9084f8255a063347a6ea05e4155e0e6077a9aafbde7bd5c7399939_wide.csv
  Loading: 2190a0da2b794d4ccc4e462cd89c2fdd37bced93272aafc334656a7d8cb167a2_wide.csv
  Loading: 3370f23cd7055a73bca859557669d8269438d7e42469389e5f315f4d225397eb_wide.csv
  Loading: 35029dbb4217c0f9f09917e7588b9cf52dc7c3c583ca150c08c3ff15b51e502d_wide.csv
  Loading: 401f02de69f658de9e87b74fd3155aa7295cc8a2fcb67d43988d051cb0c48767_wide.csv
  Loading: 4f3169eb15a50d3c2f5f226945c4ab5c232b3bcc192016fd24eaf00a169450e7_wide.csv
  Loading: 58a256bf9bf25361902e57fbf9dbfda7ba9742f82a5b2c81fa21b0d7c8de8351_wide.csv
  Loading: 5d3785215cff6de05330b0844799bf9de0ea0608edc22b098737ec286d325486_wide.csv
  Loading: 9f9a9d577893087d97533f4089771fbccf09222a4bffb979edd33ec43eb2ee06_wide.csv
  Loading: ab51993ac24b0a7348768385d1fd38822c7cc29b6b586cf9a98e7847dc63ac80_wide.csv
  Loading: bd0f66c3e921d37f7bac8b9f2ca5766d804a462c3bcf199048ec72bad5f7d346_wide.csv
  Loading: c0c28a757eeda2e30568e94220c96c832f06ad224f34cb0f08bc421001b1f6b3_wide.csv
  Loading: e15273aae8d4a96deec049c5ce348c7bf2552e5be53c2df269454e215549e352_wide.csv
  Loading: f52b062e0888afa06646eed2bcb152f90959a16b682c959a350d6674eee5f598_wide.csv

  Samples: 11479  |  Features: 728
  Training XGBoost...
  Done.

Computing SHAP for 200 samples across 24 output hours...

  Hour 00:00 ...  base=-3.2897  mean|SHAP|=0.00300
  Hour 01:00 ...  base=-2.1014  mean|SHAP|=0.00184
  Hour 02:00 ...  base=-1.4648  mean|SHAP|=0.00118
  Hour 03:00 ...  base=-1.0972  mean|SHAP|=0.00070
  Hour 04:00 ...  base=-0.8724  mean|SHAP|=0.00053
  Hour 05:00 ...  base=-0.7556  mean|SHAP|=0.00048
  Hour 06:00 ...  base=-0.8044  mean|SHAP|=0.00058
  Hour 07:00 ...  base=-0.9706  mean|SHAP|=0.00078
  Hour 08:00 ...  base=-1.2066  mean|SHAP|=0.00097
  Hour 09:00 ...  base=-1.9804  mean|SHAP|=0.00143
  Hour 10:00 ...  base=-2.4574  mean|SHAP|=0.00176
  Hour 11:00 ...  base=-2.7351  mean|SHAP|=0.00196
  Hour 12:00 ...  base=-2.8493  mean|SHAP|=0.00209
  Hour 13:00 ...  base=-2.7497  mean|SHAP|=0.00200
  Hour 14:00 ...  base=-3.0259  mean|SHAP|=0.00225
  Hour 15:00 ...  base=-2.9975  mean|SHAP|=0.00220
  Hour 16:00 ...  base=-2.7453  mean|SHAP|=0.00202
  Hour 17:00 ...  base=-2.8704  mean|SHAP|=0.00213
  Hour 18:00 ...  base=-2.9487  mean|SHAP|=0.00219
  Hour 19:00 ...  base=-3.2577  mean|SHAP|=0.00223
  Hour 20:00 ...  base=-3.6609  mean|SHAP|=0.00280
  Hour 21:00 ...  base=-3.7580  mean|SHAP|=0.00268
  Hour 22:00 ...  base=-3.7201  mean|SHAP|=0.00271
  Hour 23:00 ...  base=-3.8133  mean|SHAP|=0.00276

Top 10 features by mean |SHAP| across all hours:
   1. dSocdt_h19_day_minus1                               0.150512
   2. dSocdt_h20_day_minus1                               0.121843
   3. dSocdt_h14_day_minus1                               0.105364
   4. dSocdt_h23_day_minus1                               0.098457
   5. dSocdt_h15_day_minus1                               0.092675
   6. dSocdt_h4_day_minus1                                0.078709
   7. dSocdt_h21_day_minus1                               0.056973
   8. dSocdt_h3_day_minus1                                0.045417
   9. dSocdt_h12_day_minus1                               0.040812
  10. dSocdt_h5_day_minus1                                0.038516

Generating plots...
  Saved: results/xgboost/shap\shap_summary_bar.png
Traceback (most recent call last):
  File "C:\Users\chennagiri.s\Desktop\Soc\xgboost_shap_analysis.py", line 623, in <module>
    plot_beeswarm(shap_mean_hours, X_exp)
    ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\chennagiri.s\Desktop\Soc\xgboost_shap_analysis.py", line 247, in plot_beeswarm
    fv_norm = (fv - fv.min()) / (fv.ptp() + 1e-9)
                                 ^^^^^^
AttributeError: 'numpy.ndarray' object has no attribute 'ptp'
