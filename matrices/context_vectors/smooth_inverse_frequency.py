import os

import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity

from utility.hashing import convert_to_number

elmo = hub.Module("https://tfhub.dev/google/elmo/2", trainable=True)


def remove_first_principal_component(X):
    svd = TruncatedSVD(n_components=1, n_iter=7, random_state=0)
    svd.fit(X)
    pc = svd.components_
    XX = X - X.dot(pc.transpose()) * pc
    return XX


def run_sif_benchmark(sentences1, sentences2, model_path, freqs={}, a=0.001):
    total_freq = sum(freqs.values())

    embeddings = []

    # SIF requires us to first collect all sentence embeddings and then perform
    # common component analysis.
    for (sent1, sent2) in zip(sentences1, sentences2):
        tokens1 = sent1.tokens
        tokens2 = sent2.tokens

        weights1 = [a / (a + freqs.get(token, 0) / total_freq) for token in tokens1]
        weights2 = [a / (a + freqs.get(token, 0) / total_freq) for token in tokens2]

        file_name1 = str(convert_to_number(sent1.raw))
        file_name2 = str(convert_to_number(sent2.raw))

        if not os.path.isfile(os.path.join(model_path, '1', file_name1 + '.npy')):

            init = tf.initialize_all_variables()
            sess = tf.Session()
            sess.run(init)
            tf.logging.set_verbosity(tf.logging.ERROR)

            embeddings1 = \
                elmo(inputs={"tokens": [tokens1], "sequence_len": [len(tokens1)]}, signature="tokens", as_dict=True)[
                    "elmo"]
            embedding1 = sess.run(embeddings1[0])

            sess.close()

        else:
            embedding1 = np.load(os.path.join(model_path, '1', file_name1 + '.npy'))

        if not os.path.isfile(os.path.join(model_path, '2', file_name2 + '.npy')):

            init = tf.initialize_all_variables()
            sess = tf.Session()
            sess.run(init)
            tf.logging.set_verbosity(tf.logging.ERROR)

            embeddings2 = \
                elmo(inputs={"tokens": [tokens2], "sequence_len": [len(tokens2)]}, signature="tokens", as_dict=True)[
                    "elmo"]
            embedding2 = sess.run(embeddings2[0])

            sess.close()

        else:
            embedding2 = np.load(os.path.join(model_path, '2', file_name2 + '.npy'))



        embedding1 = np.average([model[token] for token in tokens1], axis=0, weights=weights1)
        embedding2 = np.average([model[token] for token in tokens2], axis=0, weights=weights2)

        embeddings.append(embedding1)
        embeddings.append(embedding2)

    embeddings = remove_first_principal_component(np.array(embeddings))
    sims = [cosine_similarity(embeddings[idx * 2].reshape(1, -1),
                              embeddings[idx * 2 + 1].reshape(1, -1))[0][0]
            for idx in range(int(len(embeddings) / 2))]

    return sims