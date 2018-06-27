# coding: utf-8

import os
import shutil
import sys

import numpy as np
from scnn import models, utils, experiment_helper
from scnn.data import LabeledDatasetWithNoise, LabeledDataset
from .pgrid import pgrid


def single_experiment(sigma, order, sigma_noise):

    Nside = 1024

    EXP_NAME = '40sim_{}sides_{}noise_{}order_{}sigma'.format(
        Nside, sigma_noise, order, sigma)

    x_raw_train, labels_raw_train, x_raw_std = experiment_helper.get_training_data(sigma, order)
    x_raw_test, labels_test, _ = experiment_helper.get_testing_data(sigma, order, sigma_noise, x_raw_std)

    ret = experiment_helper.data_preprossing(x_raw_train, labels_raw_train, x_raw_test, sigma_noise, feature_type=None)
    features_train, labels_train, features_validation, labels_validation, features_test = ret 

    training = LabeledDatasetWithNoise(features_train, labels_train, start_level=0, end_level=sigma_noise, nit=len(labels_train) // 10 )
    validation = LabeledDataset(features_validation, labels_validation)

    if order == 4:
        nsides = [Nside, Nside // 2, Nside // 4, min(Nside // 8, 128)]
    elif order == 2:
        nsides = [
            Nside, Nside // 2, Nside // 4, Nside // 8,
            min(Nside // 16, 128)
        ]
    elif order == 1:
        nsides = [
            Nside, Nside // 2, Nside // 4, Nside // 8, Nside // 16,
            min(Nside // 32, 64)
        ]
    else:
        raise ValueError('No parameters for this value of order.')

    print('#sides: {}'.format(nsides))

    indexes = utils.nside2indexes(nsides, order)

    C = 2  # number of class
    ntrain = len(x_noise_train)

    params = dict()
    params['dir_name'] = EXP_NAME

    params['eval_frequency'] = 10

    # Building blocks.
    params['brelu'] = 'b1relu'  # Activation.
    params['pool'] = 'mpool1'  # Pooling.

    # Architecture.
    params['nsides'] = nsides  # Sizes of the laplacians are 12 * nsides**2.
    params['indexes'] = indexes  # Sizes of the laplacians are 12 * nsides**2.
    if order == 4:
        params['num_epochs'] = 50
        params['batch_size'] = 20        
        params['F'] = [40, 160, 320,
                       20]  # Number of graph convolutional filters.
        params['K'] = [10, 10, 10, 10]  # Polynomial orders.
        params['batch_norm'] = [True, True, True, True]  # Batch norm

    elif order == 2:
        params['num_epochs'] = 100
        params['batch_size'] = 15
        params['F'] = [10, 80, 320, 40,
                       10]  # Number of graph convolutional filters.
        params['K'] = [10, 10, 10, 10, 10]  # Polynomial orders.
        params['batch_norm'] = [True, True, True, True, True]  # Batch norm
    elif order == 1:
        params['num_epochs'] = 300
        params['batch_size'] = 10
        params['F'] = [10, 40, 160, 40, 20,
                       10]  # Number of graph convolutional filters.
        params['K'] = [10, 10, 10, 10, 10, 10]  # Polynomial orders.
        params['batch_norm'] = [True, True, True, True, True,
                                True]  # Batch norm
    else:
        raise ValueError('No parameter for this value of order.')

    params['M'] = [100, C]  # Output dimensionality of fully connected layers.

    # Optimization.
    params['decay_rate'] = 0.98
    params['regularization'] = 1e-4
    params['dropout'] = 0.5
    params['learning_rate'] = 1e-4
    params['momentum'] = 0.9
    params['adam'] = True
    params['decay_steps'] = 153.6

    model = models.scnn(**params)

    # Cleanup before running again.
    shutil.rmtree('summaries/{}/'.format(EXP_NAME), ignore_errors=True)
    shutil.rmtree('checkpoints/{}/'.format(EXP_NAME), ignore_errors=True)

    accuracy, loss, t_step = model.fit(training, validation)

    error_validation = experiment_helper.model_error(model, features_validation, labels_validation)
    print('The validation error is {}%'.format(error_validation * 100), flush=True)

    error_test = experiment_helper.model_error(model, features_test, labels_test)
    print('The testing error is {}%'.format(error_test * 100), flush=True)

    return error_test


if __name__ == '__main__':

    if len(sys.argv) > 1:
        sigma = int(sys.argv[1])
        order = int(sys.argv[2])
        sigma_noise = float(sys.argv[3])
        grid = [(sigma, order, sigma_noise)]
    else:
        grid = pgrid()
    path = 'results/scnn/'

    os.makedirs(path, exist_ok=True)
    for p in grid:
        sigma, order, sigma_noise = p
        print('Launch experiment for {}, {}, {}'.format(sigma, order, sigma_noise))
        res = single_experiment(sigma, order, sigma_noise)
        filepath = os.path.join(path, 'scnn_results_list_sigma{}'.format(sigma))
        new_data = [order, sigma_noise, res]
        if os.path.isfile(filepath+'.npz'):
            results = np.load(filepath+'.npz')['data'].tolist()
        else:
            results = []
        results.append(new_data)
        np.savez(filepath, data=results)
