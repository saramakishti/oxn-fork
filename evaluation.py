#! /usr/bin/env python
"""Evaluate experiment reports created by oxn"""
import itertools
from typing import List

# TODO: figure out a way to use multiple feature columns
# TODO: handle multiple interactions
# TODO: refactor trace/metric models common functionality into base class
# TODO: add descriptive methods for stats and so on


# required so that gevent does not complain
from gevent import monkey

monkey.patch_all()
import datetime
import os.path

from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import confusion_matrix, precision_recall_curve, classification_report, f1_score, accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.model_selection import learning_curve
from imblearn.over_sampling import SMOTE

import numpy as np
import pandas as pd
import yaml
import seaborn as sns
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates
import matplotlib.ticker as mticker

from matplotlib import pyplot as plt
from oxn.store import get_dataframe

import argparse


class TraceModel:
    """A classifier to predict treatment labels from a trace response variable"""

    def __init__(self, experiment_data, feature_columns, categorical_columns, label_column, score="f1"):
        self.experiment_data = experiment_data
        self.feature_columns = feature_columns
        self.categorical_columns = categorical_columns
        self.label_column = label_column
        self.score = score
        self.x_train = None
        self.x_test = None
        self.y_train = None
        self.y_test = None
        self.classifier = None
        self.predictions = None

    def build_lr(self, split=0.3, folds=2):
        """Build a logistic regression classifier"""
        y = self.experiment_data[self.label_column]
        x = pd.concat([self.experiment_data[self.feature_columns]], axis=1)
        le = LabelEncoder()
        y = le.fit_transform(y)
        smote = SMOTE(random_state=0)
        scaler = StandardScaler()
        x_resampled, y_resampled = smote.fit_resample(x, y)
        x_train, x_test, y_train, y_test = train_test_split(x_resampled, y_resampled, test_size=split)
        x_train = scaler.fit_transform(x_train)
        x_test = scaler.transform(x_test)
        classifier = LogisticRegressionCV(solver="newton-cholesky", penalty="l2", n_jobs=-1, cv=folds,
                                          scoring=self.score)
        classifier.fit(x_train, y_train)
        self.x_train = x_train
        self.x_test = x_test
        self.y_train = y_train
        self.y_test = y_test
        self.classifier = classifier
        self.predictions = self.classifier.predict(self.x_test)

    def build_gb(self, split=0.3):
        """Build a gradient boosting classifier"""
        y = self.experiment_data[self.label_column]
        x = pd.concat([self.experiment_data[self.feature_columns]], axis=1)
        le = LabelEncoder()
        y = le.fit_transform(y)
        smote = SMOTE(random_state=0)
        scaler = StandardScaler()
        x_resampled, y_resampled = smote.fit_resample(x, y)
        x_train, x_test, y_train, y_test = train_test_split(x_resampled, y_resampled, test_size=split)
        x_train = scaler.fit_transform(x_train)
        x_test = scaler.transform(x_test)
        classifier = HistGradientBoostingClassifier(learning_rate=0.01, l2_regularization=0.1, max_depth=2)
        classifier.fit(x_train, y_train)
        self.x_train = x_train
        self.x_test = x_test
        self.y_train = y_train
        self.y_test = y_test
        self.classifier = classifier
        self.predictions = self.classifier.predict(self.x_test)

    def cross_predict(self, other_response, other_label, split=0.3):
        """Try to predict fault labels from another response"""
        y = other_response[other_label]
        operation = pd.get_dummies(other_response["operation"], prefix="operation")
        x = pd.concat([other_response[self.feature_columns], operation], axis=1)
        le = LabelEncoder()
        y = le.fit_transform(y)
        smote = SMOTE(random_state=0)
        scaler = StandardScaler()
        x_resampled, y_resampled = smote.fit_resample(x, y)
        x_train, x_test, y_train, y_test = train_test_split(x_resampled, y_resampled, test_size=split)
        x_train = scaler.fit_transform(x_train)
        x_test = scaler.transform(x_test)
        cross_predictions = self.classifier.predict(x_test)
        return f1_score(y_test, cross_predictions, average="macro")

    def scores(self):
        return classification_report(self.y_test, self.predictions)

    def plot_confusion_matrix(self, write=False):
        cm = confusion_matrix(self.y_test, self.predictions)
        plt.figure(figsize=(6, 4))
        sns.heatmap(cm, annot=True, fmt=".0f", linewidths=.5, square=True, cmap='Blues_r')
        plt.ylabel("Actual")
        plt.xlabel("Predicted")
        plt.title(f"Confusion Matrix [{self.classifier.__class__.__name__}]", size=15)
        plt.show(block=False)
        if write:
            plt.savefig(f"cm_{self.feature_columns}_{self.label_column}.png")

    def plot_precision_recall_curve(self, write=False):
        precision, recall, _ = precision_recall_curve(self.y_test, self.predictions)
        plt.figure(figsize=(5, 5))
        plt.plot(recall, precision)
        plt.xlabel('Recall')
        plt.ylabel('Precision')
        plt.title('Precision-Recall Curve')
        plt.show(block=False)
        if write:
            plt.savefig(f"prcurve_{self.feature_columns}_{self.label_column}.png")

    def plot_lr_learning_curve(self, folds=5, write=False):
        y = self.experiment_data[self.label_column]
        categorical_features = [
            pd.get_dummies(self.experiment_data[column], prefix=column) for column in self.categorical_columns
        ]
        categorical_features = pd.concat(categorical_features, axis=1)
        x = pd.concat([self.experiment_data[self.feature_columns], categorical_features], axis=1)
        le = LabelEncoder()
        y = le.fit_transform(y)
        smote = SMOTE(random_state=0)
        scaler = StandardScaler()
        x_resampled, y_resampled = smote.fit_resample(x, y)
        x_resampled = scaler.fit_transform(x_resampled)
        train_sizes, train_scores, test_scores = learning_curve(
            LogisticRegression(),
            x_resampled,
            y_resampled,
            cv=folds,
            scoring=self.score,
            n_jobs=-1,
            train_sizes=np.linspace(0.01, 1.0, 10)
        )

        # Calculate mean and standard deviation for training set scores
        train_mean = np.mean(train_scores, axis=1)
        # Calculate mean and standard deviation for test set scores
        test_mean = np.mean(test_scores, axis=1)
        # Plot mean accuracy scores for training and test sets
        plt.figure(figsize=(5, 5))
        plt.plot(train_sizes, train_mean, label="Training score")
        plt.plot(train_sizes, test_mean, label="Cross-validation score")

        # Create plot
        plt.title("Learning Curve")
        plt.xlabel("Training Set Size"), plt.ylabel("Accuracy Score"), plt.legend(loc="best")
        plt.tight_layout()
        plt.show(block=False)
        if write:
            plt.savefig(f"lr_lcurve_{self.feature_columns}_{self.label_column}.png")

    def visibility_score(self):
        """The fault visibility score is defined as the macro f1 score for the classifier"""
        if self.score == "f1":
            return f1_score(self.y_test, self.predictions)
        if self.score == "accuracy":
            return accuracy_score(self.y_test, self.predictions)

    def print_scores(self):
        print(self)
        print(self.scores())

    def __str__(self):
        return f"{self.__class__.__name__}(clf={self.classifier.__class__.__name__})"

    def __repr__(self):
        return self.__str__()


class MetricModel:
    """A classifier to predict treatment labels from a metric response variable"""

    def __init__(self, experiment_data, feature_columns, label_column, score="f1"):
        self.experiment_data = experiment_data
        self.feature_columns = feature_columns
        self.label_column = label_column
        self.x_train = None
        self.x_test = None
        self.y_train = None
        self.y_test = None
        self.classifier = None
        self.predictions = None
        self.score = score

    def build_lr(self, split=0.3, folds=5):
        """Build a logistic regression classifier for a metric response variable"""
        y = self.experiment_data[self.label_column]
        x = self.experiment_data[self.feature_columns]
        le = LabelEncoder()
        y = le.fit_transform(y)
        smote = SMOTE(random_state=0)
        scaler = StandardScaler()
        x_resampled, y_resampled = smote.fit_resample(x, y)
        x_train, x_test, y_train, y_test = train_test_split(x_resampled, y_resampled, test_size=split)
        x_train = scaler.fit_transform(x_train)
        x_test = scaler.transform(x_test)
        classifier = LogisticRegressionCV(solver="newton-cholesky", penalty="l2", cv=folds, scoring=self.score,
                                          n_jobs=-1)
        classifier.fit(x_train, y_train)
        self.x_train = x_train
        self.x_test = x_test
        self.y_train = y_train
        self.y_test = y_test
        self.classifier = classifier
        self.predictions = self.classifier.predict(self.x_test)

    def build_gb(self, split=0.3):
        """Build a gradient boosting classifier for a metric repsonse variable"""
        y = self.experiment_data[self.label_column]
        x = pd.concat([self.experiment_data[self.feature_columns]], axis=1)
        le = LabelEncoder()
        y = le.fit_transform(y)
        smote = SMOTE(random_state=0)
        scaler = StandardScaler()
        x_resampled, y_resampled = smote.fit_resample(x, y)
        x_train, x_test, y_train, y_test = train_test_split(x_resampled, y_resampled, test_size=split)
        x_train = scaler.fit_transform(x_train)
        x_test = scaler.transform(x_test)
        classifier = HistGradientBoostingClassifier()
        classifier.fit(x_train, y_train)
        self.x_train = x_train
        self.x_test = x_test
        self.y_train = y_train
        self.y_test = y_test
        self.classifier = classifier
        self.predictions = self.classifier.predict(self.x_test)

    def cross_predict(self, other_response, other_label, split=0.3):
        """Try to predict fault labels from another response"""
        x = pd.concat([other_response[self.feature_columns]], axis=1)
        # this only works if the response variable is the same for the cross prediction
        y = other_response[other_label]
        le = LabelEncoder()
        y = le.fit_transform(y)
        smote = SMOTE(random_state=0)
        scaler = StandardScaler()
        x_resampled, y_resampled = smote.fit_resample(x, y)
        x_train, x_test, y_train, y_test = train_test_split(x_resampled, y_resampled, test_size=split)
        x_train = scaler.fit_transform(x_train)
        x_test = scaler.transform(x_test)
        cross_predictions = self.classifier.predict(x_test)
        return f1_score(y_test, cross_predictions, average="macro")

    def plot_lr_learning_curve(self, folds=10, write=False):
        y = self.experiment_data[self.label_column]
        x = pd.concat([self.experiment_data[self.feature_columns]], axis=1)
        le = LabelEncoder()
        y = le.fit_transform(y)
        smote = SMOTE(random_state=0)
        scaler = StandardScaler()
        x_resampled, y_resampled = smote.fit_resample(x, y)
        x_resampled = scaler.fit_transform(x_resampled)
        train_sizes, train_scores, test_scores = learning_curve(
            LogisticRegression(),
            x_resampled,
            y_resampled,
            cv=folds,
            scoring='f1',
            n_jobs=-1,
            train_sizes=np.linspace(0.01, 1.0, 10)
        )

        # Calculate mean and standard deviation for training set scores
        train_mean = np.mean(train_scores, axis=1)
        train_std = np.std(train_scores, axis=1)

        # Calculate mean and standard deviation for test set scores
        test_mean = np.mean(test_scores, axis=1)
        test_std = np.std(test_scores, axis=1)

        # Plot mean accuracy scores for training and test sets
        plt.figure(figsize=(5, 5))
        plt.plot(train_sizes, train_mean, label="Training score")
        plt.plot(train_sizes, test_mean, label="Cross-validation score")

        # Plot accuracy bands for training and test sets
        plt.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, color="#DDDDDD")
        plt.fill_between(train_sizes, test_mean - test_std, test_mean + test_std, color="#DDDDDD")

        # Create plot
        plt.title("Learning Curve")
        plt.xlabel("Training Set Size"), plt.ylabel("Accuracy Score"), plt.legend(loc="best")
        plt.tight_layout()
        plt.show(block=False)
        if write:
            plt.savefig(f"lr_lcurve_{self.feature_columns}_{self.label_column}.png")

    def scores(self):
        return classification_report(self.y_test, self.predictions)

    def visibility_score(self):
        """The fault visibility score is defined as the macro f1 score for the classifier"""
        if self.score == "f1":
            return f1_score(self.y_test, self.predictions, average="macro")
        if self.score == "accuracy":
            return accuracy_score(self.y_test, self.predictions)

    def print_scores(self):
        print(self)
        print(self.scores())

    def __str__(self):
        return f"{self.__class__.__name__}(clf={self.classifier.__class__.__name__})"

    def __repr__(self):
        return self.__str__()

    def plot_confusion_matrix(self, write=False):
        cm = confusion_matrix(self.y_test, self.predictions)
        plt.figure(figsize=(5, 5))
        sns.heatmap(cm, annot=True, fmt=".0f", linewidths=.5, square=True, cmap='Blues_r')
        plt.ylabel("Actual")
        plt.xlabel("Predicted")
        plt.title(f"Confusion Matrix [{self.classifier.__class__.__name__}]", size=15)
        plt.show(block=False)
        if write:
            plt.savefig(f"cm_{self.feature_columns}_{self.label_column}.png")

    def plot_precision_recall_curve(self, write=False):
        precision, recall, _ = precision_recall_curve(self.y_test, self.predictions)
        plt.figure(figsize=(5, 5))
        plt.plot(recall, precision)
        plt.xlabel('Recall')
        plt.ylabel('Precision')
        plt.title('Precision-Recall Curve')
        plt.legend(loc="lower left")
        plt.show(block=False)
        if write:
            plt.savefig(f"prcurve_{self.feature_columns}_{self.label_column}.png")


class Interaction:
    def __init__(self, id, data):
        self.id = id
        self.treatment_name = data['treatment_name']
        self.treatment_start = data['treatment_start']
        self.treatment_end = data['treatment_end']
        self.treatment_type = data['treatment_type']
        self.response_name = data['response_name']
        self.response_start = data['response_start']
        self.response_end = data['response_end']
        self.response_type = data['response_type']
        self.p_value = data['p_value']
        self.test_statistic = data['test_statistic']
        self.test_performed = data['test_performed']
        self.store_key = data['store_key']
        if self.store_key:
            self.response_data = self.get_data()

    def get_data(self):
        return get_dataframe(key=self.store_key)

    def get_trace_model(self, score="f1", use_traces=True):
        """Build a logistic regression for predicting treatment labels from response data"""
        experiment_data = self.get_data()
        if use_traces:
            experiment_data = self.trace_durations()
        model = TraceModel(
            experiment_data=experiment_data,
            feature_columns=["duration"],
            categorical_columns=["operation"],
            label_column=self.treatment_name,
            score=score
        )
        return model

    def get_metric_name(self):
        if not self.response_type == "MetricResponseVariable":
            return ""
        return self.response_name

    def get_metric_model(self, score="f1"):
        model = MetricModel(
            experiment_data=self.get_data(),
            feature_columns=[self.get_metric_name()],
            label_column=self.treatment_name,
            score=score,
        )
        return model

    def get_model(self, score="f1", use_traces=False):
        if self.response_type == "TraceResponseVariable":
            return self.get_trace_model(score=score, use_traces=use_traces)
        if self.response_type == "MetricResponseVariable":
            return self.get_metric_model(score=score)


    def plot_trace_interaction(self, ax=None, color_services=False, write=False):
        """Plot a treatment-response interaction for a trace response variable"""
        response_df = self.response_data
        response_df.start_time = pd.to_datetime(response_df.start_time, unit="us")
        response_df.end_time = pd.to_datetime(response_df.end_time, unit="us")


        # all values are in microseconds, convert to milliseconds
        response_df.duration = response_df.duration / 1000
        
        if color_services:
            sns.scatterplot(ax=ax, x=response_df.start_time, y=response_df.duration, hue=response_df.service_name)
        else:
            sns.scatterplot(ax=ax, x=response_df.start_time, y=response_df.duration, color="b")
        
        # Extract treatment start and end times
        treatment_start_time = pd.to_datetime(self.treatment_start)
        treatment_end_time = pd.to_datetime(self.treatment_end)
        
        # Set up x-axis to show time at regular intervals
        ax.xaxis.set_major_locator((mticker.MaxNLocator(5)))  # Automatically adjust tick positions
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))  # Format as HH:MM:SS

        # Add vertical lines for treatment start and end times
        ax.axvline(x=treatment_start_time, color="gray", linewidth=1, linestyle="--", label="t0")
        ax.axvline(x=treatment_end_time, color="gray", linewidth=1, linestyle="--", label="t1")

        # Save existing ticks generated by AutoDateLocator
        existing_ticks = ax.get_xticks()
        
        # Add t0 and t1 manually to ensure they are always present
        ticks_with_treatment = sorted(list(set(existing_ticks).union([mdates.date2num(treatment_start_time), mdates.date2num(treatment_end_time)])))
        ax.set_xticks(ticks_with_treatment)

        # Generate tick labels for all times and customize t0 and t1 labels
        tick_labels = [mdates.num2date(tick).strftime("%H:%M:%S") for tick in ticks_with_treatment]
        for i, tick in enumerate(ticks_with_treatment):
            if tick == mdates.date2num(treatment_start_time):
                tick_labels[i] = f"t0"
            elif tick == mdates.date2num(treatment_end_time):
                tick_labels[i] = f"t1"
        
        ax.set_xticklabels(tick_labels, rotation=90)  # Rotate x-axis labels by 90 degrees

        # Set labels and title
        ax.set(xlabel="Time", ylabel="Duration [ms]", title=f"Trace Duration ({self.response_name} \n {self.treatment_name})")

        # Remove top and right spines
        sns.despine(ax=ax)
        
        # Save plot if write is True
        if write:
            plt.savefig(f"{self.treatment_name}_{self.response_name}.png")


    def plot_metric_interaction(self, ax=None, write=False):
        """Plot a treatment-response interaction for a metric response variable"""
        response_df = self.response_data
        metric_name = self.get_metric_name()

        # Plot the metric response
        sns.lineplot(ax=ax, x=response_df.index, y=response_df[metric_name])
        
        # Set title and labels
        ax.set(title=f"{metric_name} \n({self.treatment_name})")
        ax.set(ylabel="")

        # Extract treatment start and end times
        treatment_start_time = pd.to_datetime(self.treatment_start)
        treatment_end_time = pd.to_datetime(self.treatment_end)
        
        start_time_without_date = treatment_start_time.strftime("%H:%M:%S")
        end_time_without_date = treatment_end_time.strftime("%H:%M:%S")

        # Ensure proper datetime handling with mdates
        ax.xaxis.set_major_locator((mticker.MaxNLocator(5)))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

        # Add vertical lines for treatment start and end times
        ax.axvline(x=treatment_start_time, color="gray", linewidth=1, linestyle="--", label="t0")
        ax.axvline(x=treatment_end_time, color="gray", linewidth=1, linestyle="--", label="t1")

        # Set x-axis ticks to include t0 and t1
        existing_ticks = ax.get_xticks()  # Get existing ticks
        ticks_with_treatment = sorted(list(set(existing_ticks).union([mdates.date2num(treatment_start_time), mdates.date2num(treatment_end_time)])))
        ax.set_xticks(ticks_with_treatment)

        # Customize tick labels for t0 and t1
        tick_labels = [mdates.num2date(tick).strftime("%H:%M:%S") for tick in ticks_with_treatment]
        for i, tick in enumerate(ticks_with_treatment):
            if tick == mdates.date2num(treatment_start_time):
                tick_labels[i] = f"t0"
            elif tick == mdates.date2num(treatment_end_time):
                tick_labels[i] = f"t1"
        
        # Set rotated x-axis tick labels
        ax.set_xticklabels(tick_labels, rotation=90)

        # Set xlabel as empty to match the previous behavior
        ax.set(xlabel="")

        # Remove top and right spines
        sns.despine(ax=ax)

        # Save plot if requested
        if write:
            plt.savefig(f"{self.treatment_name}_{self.response_name}.png")

    def plot_interaction(self, ax=None, color_services=False, write=False):
        """Plot a response-treatment interaction depending on the type of response variable observed"""
        if not ax:
            fig, ax = plt.subplots(figsize=(5, 5))
        if self.response_type == "TraceResponseVariable":
            self.plot_trace_interaction(ax=ax, color_services=color_services, write=write)
        if self.response_type == "MetricResponseVariable":
            self.plot_metric_interaction(ax=ax, write=write)

    def trace_durations(self):
        """
        Compute a new dataframe of traces indexed by trace start time
        Traces are aggregated from spans by taking the min and max for start and end time of the span set,
        and if any treatment label is present in the span set the treatment label is propagated to the trace.
        """
        if not self.response_type == "TraceResponseVariable":
            return pd.DataFrame()

        def find_treatment(labels):
            for label in labels:
                if label == self.treatment_name:
                    return label
            return "NoTreatment"

        dropped = self.response_data.reset_index(drop=True)
        durations = dropped.groupby(dropped.trace_id).agg({
            "start_time": "min",
            "end_time": "max",
            self.treatment_name: find_treatment
        })
        durations["duration"] = durations.end_time - durations.start_time
        durations["start_time"] = pd.to_datetime(durations.start_time, unit="us")
        durations["end_time"] = pd.to_datetime(durations.end_time, unit="us")
        durations = durations.set_index(durations.start_time)
        return durations

    def plot_traces(self, write=False):
        """Aggregate the span data to a trace dataframe and plot it"""
        if not self.response_type == "TraceResponseVariable":
            return
        durations = self.trace_durations()
        ax = sns.lineplot(data=durations, x=durations.start_time, y=durations.duration, color="b")
        ax.axvline(x=pd.to_datetime(self.treatment_start), color="r")
        ax.axvline(x=pd.to_datetime(self.treatment_end), color="r")
        ax.set(xlabel="Trace start timestamp")
        ax.set(ylabel="Duration [us]")
        ax.set(title=f"{self.treatment_name} [traces]")
        sns.despine(ax=ax)
        plt.xticks(rotation=90)
        plt.show(block=False)
        if write:
            plt.savefig(f"{self.treatment_name}_{self.response_name}.png")

    def get_treatment_label(self):
        return self.treatment_name

    def __str__(self):
        return f"Interaction(treatment={self.treatment_type}, response={self.response_type})"

    def __repr__(self):
        return self.__str__()


class TaskDetail:
    def __init__(self, id, data):
        self.id = id
        self.url = data.get("url", "")
        self.verb = data.get("verb", "")
        self.requests = data.get('requests', 0)
        self.failures = data.get('failures', 0)
        self.fail_ratio = data.get('fail_ratio', 0.0)
        self.sum_response_time = data.get('sum_response_time', 0)
        self.min_response_time = data.get('min_response_time', 0)
        self.max_response_time = data.get('max_response_time', 0)
        self.avg_response_time = data.get('avg_response_time', 0.0)
        self.median_response_time = data.get('median_response_time', 0)


class AccountingDetail:
    def __init__(self, id, data):
        self.id = id
        self.cpu_seconds = data.get("cpu_seconds", 0.0)
        self.number_of_cpus = data.get("number_of_cpus", 0)


class Run:
    def __init__(self, run_key, run_data):
        self.id = run_key
        self.interactions = [Interaction(id=interaction_id, data=interaction) for interaction_id, interaction in
                             run_data["interactions"].items()]
        self.loadgen_start_time = run_data["loadgen"].get('loadgen_start_time', '')
        self.loadgen_end_time = run_data["loadgen"].get('loadgen_end_time', '')
        self.loadgen_total_requests = run_data["loadgen"].get('loadgen_total_requests', 0)
        self.loadgen_total_failures = run_data["loadgen"].get('loadgen_total_failures', 0)
        self.task_details = [TaskDetail(id=k, data=v) for k, v in run_data["loadgen"].get('task_details', {}).items()]
        self.accounting_details = []
        if "accounting" in run_data:
            self.accounting_details = [AccountingDetail(id=k, data=v) for k, v in run_data["accounting"].items()]

    def __str__(self):
        return f"Run(id={self.id}, interactions={len(self.interactions)}, loadgen_tasks={len(self.task_details)})"

    def __repr__(self):
        return self.__str__()


class Report:
    def __init__(self, experiment_name, created, data):
        self.experiment_name = experiment_name
        self.created = created
        self.runs = [Run(run_key=run_key, run_data=run_data) for run_key, run_data in
                     data["report"]["runs"].items()]

    def plot_interaction_grid(self, rows, cols, interactions=None):
        n = len(interactions)

        valid_interactions = [i for i in range(len(self.interactions))]
        if not interactions:
            interactions = valid_interactions

        if rows * cols < n:
            raise ValueError("Not enough rows or columns to display all interactions")
        if rows > n:
            raise ValueError("Not enough interactions to fill all rows")
        if cols > n:
            raise ValueError("Not enough interactions to fill all columns")
        if n > len(self.interactions):
            raise ValueError("Interactions available %s" % valid_interactions)
        if n != len(interactions):
            raise ValueError("Interactions provided %s" % interactions)

        for idx in interactions:
            if idx < 0 or idx >= len(self.interactions):
                raise ValueError(
                    "Invalid interaction provided: %s. Available interactions %s " % (idx, valid_interactions))

        fig = plt.figure(figsize=(cols * 4, rows * 4))
        gs = gridspec.GridSpec(rows, cols)

        for idx, interaction_idx in enumerate(interactions):
            interaction = self.interactions[interaction_idx]
            col_idx = idx // rows
            row_idx = idx % rows
            ax = fig.add_subplot(gs[row_idx, col_idx])
            interaction.plot_interaction(ax=ax)

        fig.suptitle(self.experiment_name)
        plt.tight_layout()
        plt.show(block=False)

    def get_visibility_df(self, classifier="LR", score="f1", use_traces=False, split=0.3, folds=2) -> pd.DataFrame:
        interaction_data = []
        for interaction in self.interactions:
            interaction_model = interaction.get_model(score=score, use_traces=use_traces)
            if classifier == "GBT":
                interaction_model.build_gb(split=split)
            if classifier == "LR":
                interaction_model.build_lr(split=split, folds=folds)
            interaction_data.append([
                self.experiment_name,
                interaction.treatment_name,
                interaction.treatment_type,
                interaction.response_name,
                interaction.response_type,
                classifier,
                interaction_model.visibility_score()])
        columns = [
            "report",
            "treatment_name",
            "treatment_type",
            "response_name",
            "response_type",
            "classifier",
            f"visibility[{score}]"
        ]
        df = pd.DataFrame(interaction_data, columns=columns)
        return df

    @property
    def interactions(self) -> List[Interaction]:
        """Concatenate all the interactions from each run"""
        interactions = []
        for run in self.runs:
            for interaction in run.interactions:
                interactions.append(interaction)
        return interactions

    @property
    def accounting_data(self) -> pd.DataFrame:
        """Return the accounting data from each run"""
        header = ["run_key", "service", "cpu_seconds", "number_of_cpus"]
        data = []
        for run in self.runs:
            accounting_details = run.accounting_details
            for detail in accounting_details:
                data.append([run.id, detail.id, detail.cpu_seconds, detail.number_of_cpus])
        performance_df = pd.DataFrame.from_records(data)
        performance_df.columns = header
        return performance_df

    @property
    def loadgen_data(self) -> pd.DataFrame:
        """Return the load generation data from each run"""
        header = ["run_key", "task_id", "url", "verb",
                  "requests", "failures", "sum_response_time", "min_response_time", "max_response_time",
                  "avg_response_time", "median_response_time",
                  ]
        data = []
        for run in self.runs:
            for loadgen_detail in run.task_details:
                data.append([
                    run.id,
                    loadgen_detail.id,
                    loadgen_detail.url,
                    loadgen_detail.verb,
                    loadgen_detail.requests,
                    loadgen_detail.failures,
                    loadgen_detail.sum_response_time,
                    loadgen_detail.min_response_time,
                    loadgen_detail.max_response_time,
                    loadgen_detail.avg_response_time,
                    loadgen_detail.median_response_time
                ])
        loadgen_df = pd.DataFrame.from_records(data)
        loadgen_df.columns = header
        return loadgen_df

    def __str__(self):
        return f"{self.__class__.__name__}(file={self.experiment_name}, created={self.created})"

    @classmethod
    def from_file(cls, report_path):
        with open(report_path, "r") as report_file:
            report_data = yaml.safe_load(report_file.read())
        creation_time = datetime.datetime.fromtimestamp(os.path.getctime(report_path))
        return cls(experiment_name=report_path, created=creation_time, data=report_data)


def valid_split_range(n):
    n = float(n)
    if n < 0 or n > 1:
        raise argparse.ArgumentTypeError("Split must be between 0 and 1")
    return n


parser = argparse.ArgumentParser(
    prog="evaluation",
    description="Build fault prediction models and visualize experiment data from oxn"
)

parser.add_argument(
    "reports",
    help="Reports to evaluate",
    nargs="+",
)

parser.add_argument(
    "--classifier",
    help="Specify which classifier to use",
    action="append",
    choices=["GBT", "LR"],
    default=[],
)

parser.add_argument(
    "--plot",
    help="Specify which plots to output",
    action="append",
    choices=["cm", "prcurve", "data", "lcurve", "traces"],
    default=[],
)
parser.add_argument(
    "--score",
    help="Specify which classification score to use for fault visibility",
    action="store",
    choices=["f1", "accuracy"]
)
parser.add_argument(
    "--split",
    help="Specify the test data size. Must be between 0 and 1",
    type=valid_split_range,
    default=0.3
)
parser.add_argument(
    "--folds",
    help="The number of cross-validation folds to use for the classifier",
    default=10,
    type=int,
)
parser.add_argument(
    "--write-plots",
    help="Write the plots to disk",
    action="store_true"
)
parser.add_argument(
    "--cross",
    help="Compute cross-predictions to evaluate fault ambiguity",
    action="store_true",
)
parser.add_argument(
    "--use-traces",
    help="Use aggregated traces to train the model instead of raw spans",
    action="store_true",
)

if __name__ == "__main__":
    args = parser.parse_args()
    # build report objects for each report
    reports = [Report.from_file(report_path=report) for report in args.reports]
    models = []
    visibility_data = []
    ambiguity_data = []

    if args.cross and len(args.classifier) > 1:
        parser.error(message="Cross-prediction is only allowed for a single classifier")

    for report in reports:
        for interaction in report.interactions:
            for plot in args.plot:
                if plot == "data":
                    interaction.plot_interaction(write=args.write_plots)
                    plt.show()
                if plot == "traces":
                    interaction.plot_traces(write=args.write_plots)
                    plt.show()
    for classifier in args.classifier:
        for report in reports:
            for interaction in report.interactions:
                model = interaction.get_model(score=args.score, use_traces=args.use_traces)
                dataframe = interaction.get_data()
                if classifier == "GBT":
                    model.build_gb(split=args.split)
                if classifier == "LR":
                    model.build_lr(split=args.split, folds=args.folds)
                visibility_data.append([
                    str(report),
                    interaction.treatment_name,
                    interaction.treatment_type,
                    interaction.response_name,
                    interaction.response_type,
                    classifier,
                    model.visibility_score()])
                models.append((report, model))
                for plot in args.plot:
                    if plot == "cm":
                        model.plot_confusion_matrix(write=args.write_plots)
                    if plot == "prcurve":
                        model.plot_precision_recall_curve(write=args.write_plots)
                    if plot == "lcurve":
                        model.plot_lr_learning_curve(write=args.write_plots)
                    plt.show()
    if visibility_data:
        visibility_df = pd.DataFrame(visibility_data, columns=[
            "report",
            "treatment_name",
            "treatment_type",
            "response_name",
            "response_type",
            "classifier",
            f"visibility[{args.score}]"
        ])
        print(visibility_df)
