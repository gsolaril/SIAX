import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

class DataFramePlotting:

  @staticmethod
  def configure_plot(font_color = 'yellow'):
    mpl.rcParams['figure.figsize'] = (30, 15)
    mpl.rcParams['axes.grid'] = False
    mpl.rcParams.update({'font.size': 18})

    mpl.rcParams['text.color'] = font_color
    mpl.rcParams['axes.labelcolor'] = font_color
    mpl.rcParams['xtick.color'] = font_color
    mpl.rcParams['ytick.color'] = font_color

  @staticmethod
  def plot_columns(df, columns, datetime_index, subplots = True, from_idx = 0, to_idx=None):
    """
    From a dataframe, plots the provided columns using the
    provided datetime index. 
    """
    plot_features = df[columns][from_idx:to_idx]
    plot_features.index = datetime_index[from_idx:to_idx]
    _ = plot_features.plot(subplots=subplots)

  @staticmethod
  def plot_frequencies(x_steps, y_steps):
    plt.step(abs(x_steps), np.abs(y_steps))
    plt.xscale('log')
    plt.ylim(0, 400000)
    plt.xlim([0.1, max(plt.xlim())])
    _ = plt.xlabel('Frequency (log scale)')

  @staticmethod
  def plot_distributions(df, train_mean = 0, train_std = 1):
    """
    Plots the distribution of all columns of the dataframe.
    It substracts the mean and divides by the std.
    """
    df_std = (df - train_mean) / train_std
    df_std = df_std.melt(var_name='Column', value_name='Normalized')
    ax = sns.violinplot(x='Column', y='Normalized', data=df_std)
    _ = ax.set_xticklabels(df.keys(), rotation=90)