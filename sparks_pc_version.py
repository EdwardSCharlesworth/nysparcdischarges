#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  1 10:36:12 2019

@author: User
"""
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.externals import joblib
from sklearn.model_selection import train_test_split
from sklearn.datasets import dump_svmlight_file
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import f1_score, accuracy_score,precision_recall_curve,roc_auc_score, roc_curve, average_precision_score
import matplotlib.pyplot as plt
from sklearn.utils.fixes import signature
import gc

#file_2014 = r"C:\Users\User\Desktop\Hospital_Inpatient_Discharges__SPARCS_De-Identified___2014.csv"
#replace with scraper
file_2015 = r"C:\Users\User\Desktop\Hospital_Inpatient_Discharges__SPARCS_De-Identified___2015.csv"

sparcs_2015 = pd.read_csv(file_2015,engine='python')
#sparcs_2014 = pd.read_csv(file_2014,engine='python')

def clean(data):
    data.columns = data.columns.str.strip().str.upper().str\
    .replace(' ', '_').str.replace('(', '').str.replace(')', '')
    return data

sparcs_2015 = clean(sparcs_2015)
#sparcs_2014 = clean(sparcs_2014)
#2015
numeric_cols = [cname for cname in sparcs_2015.columns if
                sparcs_2015[cname].dtype in ['int64', 'float64']]
for columns in numeric_cols:
    sparcs_2015[columns].fillna(0, inplace=True)

text_cols = [cname for cname in sparcs_2015.columns if
             sparcs_2015[cname].dtype not in ['int64', 'float64']]

for columns in text_cols:
    sparcs_2015[columns].fillna("NA", inplace=True)

##2014
#numeric_cols = [cname for cname in sparcs_2014.columns if
#              sparcs_2014[cname].dtype in ['int64', 'float64']]
#
#for columns in numeric_cols:
#    sparcs_2014[columns].fillna(0, inplace=True)
#
#text_cols = [cname for cname in sparcs_2014.columns if
#           sparcs_2014[cname].dtype not in ['int64', 'float64']]
#
#for columns in text_cols:
#    sparcs_2014[columns].fillna("NA", inplace=True)
#%%
#sparcs_2015 = sparcs_2015.sample(frac=0.01, replace=True, random_state=1).reset_index()
le = LabelEncoder()
sparcs_2015['APR_RISK_OF_MORTALITY'] = sparcs_2015['APR_RISK_OF_MORTALITY'].replace("NA","Minor")
le.fit(["Minor", "Moderate", "Major", "Extreme"])
y = le.transform(sparcs_2015['APR_RISK_OF_MORTALITY'])

equiv_mort = {'Minor':0, 'Moderate':0, 'Major':0, 'Extreme': 1}
sparcs_2015['y_binary'] = sparcs_2015['APR_RISK_OF_MORTALITY'].map(equiv_mort)
y_binary=sparcs_2015['y_binary'].values
new_y_binary=sparcs_2015['y_binary']
proposed_X = sparcs_2015.drop(['y_binary','TOTAL_CHARGES','TOTAL_COSTS','APR_RISK_OF_MORTALITY',
                               'DISCHARGE_YEAR'],axis=1)

low_cardinality_cols = [cname for cname in proposed_X.columns if
                        proposed_X[cname].nunique() < 10 and
                        proposed_X[cname].dtype == "object"]

numeric_cols = [cname for cname in proposed_X.columns if
                proposed_X[cname].dtype in ['int64', 'float64']]

my_cols = low_cardinality_cols + numeric_cols

# One hot encoded
one_hot_encoded_X=pd.get_dummies(proposed_X[my_cols])
print("# of columns: {0}"\
      .format(len(one_hot_encoded_X.columns)))
one_hot_encoded_X=clean(one_hot_encoded_X)

features=list(one_hot_encoded_X.columns)

del proposed_X
del sparcs_2015
gc.collect()
#%%

#using randomized search
from sklearn.model_selection import RandomizedSearchCV
from sklearn.model_selection import ShuffleSplit
clf_xgb = xgb.XGBClassifier(objective = 'binary:logistic')
param_dist = {'silent': [False],
        'max_depth': [6, 10, 15, 20],
        'learning_rate': [0.001, 0.01, 0.1, 0.2, .3, .4, 0,3],
        'subsample': [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        'colsample_bytree': [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        'colsample_bylevel': [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        'min_child_weight': [0.5, 1.0, 3.0, 5.0, 7.0, 10.0],
        'gamma': [0, 0.25, 0.3, 0.4, 0.5, 1.0],
        'reg_lambda': [0.1, 1.0, 5.0, 10.0, 50.0, 100.0],
        'reg_alpha': 2. ** np.arange(-13, 10, 2),
        'n_estimators': [100,150,200]
             }
clf = RandomizedSearchCV(clf_xgb, param_distributions = param_dist, 
                         n_iter = 25, 
                         scoring = 'f1', error_score = 0,
                         verbose = 3, n_jobs = -1)

rs = ShuffleSplit(n_splits=3, test_size=.25, random_state=0)
gc.collect()

estimators = []
results = np.zeros(len(one_hot_encoded_X))
score = []
for train_index, test_index in rs.split(one_hot_encoded_X):
#    print('Iteration:', i)
    X_train, X_test = one_hot_encoded_X.iloc[train_index], one_hot_encoded_X.iloc[test_index]
    y_train, y_test = new_y_binary.iloc[train_index], new_y_binary.iloc[test_index]
    clf.fit(X_train, y_train)

    estimators.append(clf.best_estimator_)
    results[test_index] = clf.predict(X_test)
    score.append(f1_score(y_test, results[test_index]))

bst.dump_model('/home/ed/Desktop/dump.raw.txt')

#%%
X_train, X_test, y_train, y_test = train_test_split(one_hot_encoded_X,
                                                   y_binary,test_size=0.2,
                                                   random_state=4)

dump_svmlight_file(X_train, y_train, 'dtrain.svm', zero_based=True)
dump_svmlight_file(X_test, y_test, 'dtest.svm', zero_based=True)
dtrain_svm = xgb.DMatrix('dtrain.svm',
                         feature_names=features)
dtest_svm = xgb.DMatrix('dtest.svm',
                        feature_names=features)

tests={}
param = {
    'max_depth':20,
    'eta':0.01,
    'silent':1,
    'objective':'multi:softmax',
    'num_class':4
    }
#param['eval_metric'] = ['auc']
num_round = 50  # the number of training iterations
watchlist = [(dtest_svm,'eval'), (dtrain_svm,'train')]

#
#    Underfitting – Validation and training error high
#
#    Overfitting – Validation error is high, training error low
#
#    Good fit – Validation error low, slightly higher than the training error
#
#    Unknown fit - Validation error low, training error 'high'

evals_result = {}
bst = xgb.train(param,dtrain_svm,
                num_round,watchlist,
                evals_result=evals_result,
                early_stopping_rounds=2)

bst.dump_model('/home/ed/Desktop/dump.raw.txt')

preds = bst.predict(dtest_svm)
y_score=preds
best_preds = np.asarray([np.argmax(line) for line in preds])

joblib.dump(bst, '/home/ed/Desktop/bst_model.pkl', compress=True)
# bst = joblib.load('bst_model.pkl') # load it later
#metrics.f1_score(y_test, y_score, average='weighted', labels=np.unique(y_score))

xgb.plot_importance(bst, importance_type='weight',max_num_features=10)

xgb.to_graphviz(bst,size="500,500!")

accuracy_score(y_test, y_score)
#%%

X_train,X_test,y_train,y_test=train_test_split(one_hot_encoded_X,y_binary,test_size=0.2,random_state=4)
xgtrain = xgb.DMatrix(X_train,label=y_train)
clf = xgb.XGBClassifier(objective='binary:logistic',missing=np.nan,max_depth = 20,
                        n_estimators=700,learning_rate=0.01,nthread=8,subsample=1.0,
                        colsample_bytree=0.85,min_child_weight = 3,#reg_lambda=1,reg_alpha=100,
                        seed=1234)
xgb_param = clf.get_xgb_params()
#cross validation
print ('Start cross validation')
cvresult=xgb.cv(xgb_param,xgtrain,num_boost_round=80,nfold=3,stratified=True,
                folds=None,metrics=(),obj=None,feval=None,maximize=False,
                early_stopping_rounds=2,fpreproc=None,as_pandas=True,
                verbose_eval=True,show_stdv=True,seed=0,callbacks=None,
                shuffle=True)

#sklearn plotting
print('Best number of trees = {}'.format(cvresult.shape[0]))
clf.set_params(n_estimators=cvresult.shape[0])
print('Fit on the training data')
clf.fit(X_train, y_train, eval_metric='auc')
print('Overall AUC:', roc_auc_score(y_train, clf.predict_proba(X_train)[:,1]))
print('Predict the probabilities on test set')
pred = clf.predict_proba(X_train, ntree_limit=cvresult.shape[0])

xgb.plot_importance(clf,max_num_features=10)

xgb.to_graphviz(clf,size="20,20!")


y_pred_xgb = clf.predict_proba(X_test)[:, 1]
fpr_grd, tpr_grd, _ = roc_curve(y_test, y_pred_xgb)


plt.figure(1)
plt.plot([0, 1], [0, 1], 'k--')
plt.plot(fpr_grd, tpr_grd, label='GBT')
plt.xlabel('False positive rate')
plt.ylabel('True positive rate')
plt.title('ROC curve')
plt.legend(loc='best')
plt.show()
plt.close()
average_precision = average_precision_score(y_test, y_pred_xgb)

print('Average precision-recall score: {0:0.2f}'.format(average_precision))
precision,recall,_ =precision_recall_curve(y_test, y_pred_xgb)
step_kwargs = ({'step': 'post'}
               if 'step' in signature(plt.fill_between).parameters
               else {})
plt.step(recall, precision, color='b', alpha=0.2,
         where='post')
plt.fill_between(recall, precision, alpha=0.2, color='b', **step_kwargs)

plt.xlabel('Recall')
plt.ylabel('Precision')
plt.ylim([0.0, 1.05])
plt.xlim([0.0, 1.0])
plt.title('Precision-Recall curve: AP={0:0.2f}'.format(average_precision))
plt.show()
plt.close()
#%%


#clf = joblib.load(r'C:\Users\User\Desktop\long_clf_model.pkl') 
xgb.plot_importance(clf,max_num_features=10)

xgb.to_graphviz(clf,size="20,20!")


y_pred_xgb = clf.predict_proba(X_test)[:, 1]
fpr_grd, tpr_grd, _ = roc_curve(y_test, y_pred_xgb)


plt.figure(1)
plt.plot([0, 1], [0, 1], 'k--')
plt.plot(fpr_grd, tpr_grd, label='GBT')
plt.xlabel('False positive rate')
plt.ylabel('True positive rate')
plt.title('ROC curve')
plt.legend(loc='best')
plt.show()
plt.close()
average_precision = average_precision_score(y_test, y_pred_xgb)

print('Average precision-recall score: {0:0.2f}'.format(average_precision))
precision,recall,_ =precision_recall_curve(y_test, y_pred_xgb)
step_kwargs = ({'step': 'post'}
               if 'step' in signature(plt.fill_between).parameters
               else {})
plt.step(recall, precision, color='b', alpha=0.2,
         where='post')
plt.fill_between(recall, precision, alpha=0.2, color='b', **step_kwargs)

plt.xlabel('Recall')
plt.ylabel('Precision')
plt.ylim([0.0, 1.05])
plt.xlim([0.0, 1.0])
plt.title('Precision-Recall curve: AP={0:0.2f}'.format(average_precision))
plt.show()
plt.close()
