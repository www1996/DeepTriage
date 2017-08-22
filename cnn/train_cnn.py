from tensorflow.contrib.tensorboard.plugins import projector
from gensim.models.word2vec import KeyedVectors
import tensorflow as tf
import os
import numpy as np
from six.moves import xrange
import time
import datetime
import data_helpers
import text_cnn

# Parameters
# ==================================================

# Data loading params
tf.flags.DEFINE_string("data_file", "../../data/eclipse/train.tfrecords",
                       "Data source for the  data TFRecords.")
tf.flags.DEFINE_string("embedding_file", "../../data/GoogleNews-vectors-negative300.bin",
                       "embedding file")
tf.flags.DEFINE_string("log_dir", "./runs/cnn_model", "log dir")

# Model Hyperparameters
tf.flags.DEFINE_integer("embedding_dim", 300, "Dimensionality of character embedding (default: 128)")
tf.flags.DEFINE_string("filter_sizes", "3,4,5",
                       "Comma-separated filter sizes (default: '3,4,5')")
tf.flags.DEFINE_integer("num_filters", 100, "Number of filters per filter size (default: 128)")
tf.flags.DEFINE_float("dropout_keep_prob", 0.5, "Dropout keep probability (default: 0.5)")
tf.flags.DEFINE_float("l2_reg_lambda", 3, "L2 regularization lambda (default: 0.0)")
tf.flags.DEFINE_float("init_learning_rate", 1e-4, "learning rate")
tf.flags.DEFINE_float("decay_rate", 0.96, "decay rate")

# Training parameters
tf.flags.DEFINE_integer("batch_size", 50, "Batch Size (default: 64)")
tf.flags.DEFINE_integer("num_epochs", 200, "Number of training epochs (default: 200)")
tf.flags.DEFINE_integer("evaluate_every", 100, "Evaluate model on dev set after this many steps (default: 100)")
tf.flags.DEFINE_integer("checkpoint_every", 100, "Save model after this many steps (default: 100)")
tf.flags.DEFINE_integer("num_checkpoints", 5, "Number of checkpoints to store (default: 5)")
tf.flags.DEFINE_integer("top_k", 3, "evaluation top k")
# Misc Parameters
tf.flags.DEFINE_boolean("allow_soft_placement", True, "Allow device soft device placement")
tf.flags.DEFINE_boolean("log_device_placement", False, "Log placement of ops on devices")
tf.flags.DEFINE_string("embedding_type", "rand", "rand, static,none_static, multiple_channels (default: 'rand')")


FLAGS._parse_flags()
print("\nParameters:")
for attr, value in sorted(FLAGS.__flags.items()):
    print("{}={}".format(attr.upper(), value))
print("")

if tf.gfile.Exists(FLAGS.log_dir):
    tf.gfile.DeleteRecursively(FLAGS.log_dir)
tf.gfile.MakeDirs(FLAGS.log_dir)

# Data Preparation
# ==================================================

## Load data
#print("Loading data...")
## ocean's training data
## x, y, vocab_processor = data_helpers.load_data_labels(FLAGS.data_file, FLAGS.label_file)
#
#data_dir = "../../data/data_by_ocean/eclipse/"
#train_files = [data_dir + str(i) + '.csv' for i in range(2)]
#test_files = [data_dir + str(i) + '.csv' for i in range(2, 3)]
#x_train, y_train, x_dev, y_dev, vocabulary_processor = data_helpers.load_files(train_files, test_files)
#
# xiaowan training data
# x_train, y_train, x_dev, y_dev, vocabulary_processor = \
#     data_helpers.load_data_labels(FLAGS.data_file, FLAGS.dev_sample_percentage)
# mine training data
# train_data = ['../../data/data_by_ocean/eclipse/raw/0_summary_description.csv',
#               '../../data/data_by_ocean/eclipse/raw/1_summary_description.csv',
#               '../../data/data_by_ocean/eclipse/raw/2_summary_description.csv',
#               '../../data/data_by_ocean/eclipse/raw/3_summary_description.csv',
#               '../../data/data_by_ocean/eclipse/raw/4_summary_description.csv',
#               '../../data/data_by_ocean/eclipse/raw/5_summary_description.csv',
#               '../../data/data_by_ocean/eclipse/raw/6_summary_description.csv',
#               '../../data/data_by_ocean/eclipse/raw/7_summary_description.csv',
#               '../../data/data_by_ocean/eclipse/raw/8_summary_description.csv']
# label_data = ['../../data/data_by_ocean/eclipse/raw/0_bug_id_date_who.csv',
#               '../../data/data_by_ocean/eclipse/raw/1_bug_id_date_who.csv',
#               '../../data/data_by_ocean/eclipse/raw/2_bug_id_date_who.csv',
#               '../../data/data_by_ocean/eclipse/raw/3_bug_id_date_who.csv',
#               '../../data/data_by_ocean/eclipse/raw/4_bug_id_date_who.csv',
#               '../../data/data_by_ocean/eclipse/raw/5_bug_id_date_who.csv',
#               '../../data/data_by_ocean/eclipse/raw/6_bug_id_date_who.csv',
#               '../../data/data_by_ocean/eclipse/raw/7_bug_id_date_who.csv',
#               '../../data/data_by_ocean/eclipse/raw/8_bug_id_date_who.csv']
# test_data = ['../../data/data_by_ocean/eclipse/raw/9_summary_description.csv',
#              '../../data/data_by_ocean/eclipse/raw/10_summary_description.csv']
# label_test_data = ['../../data/data_by_ocean/eclipse/raw/9_bug_id_date_who.csv',
#                    '../../data/data_by_ocean/eclipse/raw/10_bug_id_date_who.csv']
# x_train, y_train, x_dev, y_dev, vocab_processor = data_helpers.load_data_labels(train_data, label_data,
#                                                                                 test_data, label_test_data)

# Training
# ==================================================

with tf.Graph().as_default():
    session_conf = tf.ConfigProto(
        allow_soft_placement=FLAGS.allow_soft_placement,
        log_device_placement=FLAGS.log_device_placement)

    sess = tf.Session(config=session_conf)
    with sess.as_default():
        cnn = text_cnn.TextCNN(
            sequence_length=x_train.shape[1],
            num_classes=y_train.shape[1],
            vocab_size=len(vocabulary_processor.vocabulary_),
            embedding_size=FLAGS.embedding_dim,
            num_filters=FLAGS.num_filters,
            batch_size=FLAGS.batch_size,
            filter_sizes=list(map(int, FLAGS.filter_sizes.split(","))),
            top_k=FLAGS.top_k,
            embedding_type=FLAGS.embedding_type,
            l2_reg_lambda=FLAGS.l2_reg_lambda)

        # Define Training procedure
        global_step = tf.Variable(0, name="global_step", trainable=False)

        # add decay learning rate
        # num_batches_per_epoch = int((len(x_train) - 1) / FLAGS.batch_size) + 1
        # decay_steps = int(num_batches_per_epoch * FLAGS.num_epochs * 0.1)
        # Decay the learning rate exponentially based on the number of steps.
        # lr = tf.train.exponential_decay(FLAGS.init_learning_rate,
        #                                 global_step,
        #                                 decay_steps,
        #                                 FLAGS.decay_rate,
        #                                 staircase=True)
        lr = FLAGS.init_learning_rate
        # optimizer = tf.train.AdamOptimizer(lr)
        optimizer = tf.train.AdadeltaOptimizer(lr)
        grads_and_vars = optimizer.compute_gradients(cnn.loss)
        train_op = optimizer.apply_gradients(grads_and_vars, global_step=global_step)
        # Keep track of gradient values and sparsity (optional)
        grad_summaries = []
        for g, v in grads_and_vars:
            if g is not None:
                grad_hist_summary = tf.summary.histogram("{}/grad/hist".format(v.name), g)
                sparsity_summary = tf.summary.scalar("{}/grad/sparsity".format(v.name), tf.nn.zero_fraction(g))
                grad_summaries.append(grad_hist_summary)
                grad_summaries.append(sparsity_summary)
        grad_summaries_merged = tf.summary.merge(grad_summaries)

        # Summaries for loss and accuracy
        loss_summary = tf.summary.scalar("loss", cnn.loss)
        acc_summary = tf.summary.scalar("accuracy", cnn.accuracy)
        precision_summary = tf.summary.scalar("precision", cnn.precision)
        recall_summary = tf.summary.scalar("recall", cnn.recall)
        # Train Summaries
        train_summary_op = tf.summary.merge(
            [loss_summary, acc_summary, grad_summaries_merged, precision_summary, recall_summary])
        train_summary_dir = os.path.abspath(os.path.join(FLAGS.log_dir, "summaries", "train"))
        train_summary_writer = tf.summary.FileWriter(train_summary_dir, sess.graph)

        # validation summaries
        dev_summary_op = tf.summary.merge([loss_summary, acc_summary, precision_summary, recall_summary])
        dev_summary_dir = os.path.abspath(os.path.join(FLAGS.log_dir, "summaries", "validation"))
        dev_summary_writer = tf.summary.FileWriter(dev_summary_dir, sess.graph)

        # test summaries
        test_summary_op = tf.summary.merge([loss_summary, acc_summary, precision_summary, recall_summary])
        test_summary_dir = os.path.abspath(os.path.join(FLAGS.log_dir, "summaries", "test"))
        test_summary_writer = tf.summary.FileWriter(test_summary_dir, sess.graph)

        # Checkpoint directory. TensorFlow assumes this directory already exists so we need to create it
        checkpoint_dir = os.path.abspath(os.path.join(FLAGS.log_dir, "checkpoints"))
        checkpoint_prefix = os.path.join(checkpoint_dir, "model")
        if not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir)
        saver = tf.train.Saver(tf.global_variables().extend(tf.local_variables()), max_to_keep=FLAGS.num_checkpoints)

        # Write vocabulary
        # vocabulary_processor.save(os.path.join(FLAGS.log_dir, "vocab"))

        initW = None
        if FLAGS.embedding_type in ['static', 'none_static', 'multiple_channels']:
            # initial matrix with random uniform
            initW = np.random.uniform(-0.25, 0.25, (len(vocabulary_processor.vocabulary_), FLAGS.embedding_dim))
            # load any vectors from the word2vec
            print("Load word2vec file {}\n".format(FLAGS.embedding_file))
            word_vectors = KeyedVectors.load_word2vec_format(FLAGS.embedding_file, binary=True)
            for word in word_vectors.vocab:
                idx = vocabulary_processor.vocabulary_.get(word)
                if idx != 0:
                    initW[idx] = word_vectors[word]
            sess.run(cnn.W.assign(initW))
            if FLAGS.embedding_type == 'multiple_channels':
                sess.run(cnn.W_static.assign(initW))

        # Initialize all variables
        sess.run(tf.global_variables_initializer())
        sess.run(tf.local_variables_initializer())


        def train_step(x_batch_train, y_batch_train):
            """
            A single training step
            """
            feed_dict = {
                cnn.input_x: x_batch_train,
                cnn.input_y: y_batch_train,
                cnn.dropout_keep_prob: FLAGS.dropout_keep_prob
            }
            _, step_train, summaries, loss, accuracy, precision, recall = sess.run(
                [train_op, global_step, train_summary_op, cnn.loss, cnn.accuracy, cnn.precision, cnn.recall],
                feed_dict)
            time_str = datetime.datetime.now().isoformat()
            print(
                "{}: step {}, loss {:g}, acc {:g}, pre {:g}, rcl {:g}".format(time_str,
                                                                              step_train,
                                                                              loss,
                                                                              accuracy,
                                                                              precision,
                                                                              recall))
            train_summary_writer.add_summary(summaries, step_train)


        def dev_step(x_batch_evl, y_batch_evl, writer=None):
            """
            validate model on a dev set
            """
            feed_dict = {
                cnn.input_x: x_batch_evl,
                cnn.input_y: y_batch_evl,
                cnn.dropout_keep_prob: 1.0
            }
            step_evl, summaries, loss, accuracy, precision, recall = \
                sess.run([global_step, dev_summary_op,
                          cnn.loss, cnn.accuracy, cnn.precision, cnn.recall], feed_dict)
            time_str = datetime.datetime.now().isoformat()
            print("{}: step {}, loss {:g}, acc {:g}, prc {:g}, rcl {:g}".format(time_str, step_evl,
                                                                                loss, accuracy, precision, recall))
            if writer:
                writer.add_summary(summaries, step_evl)


        def test_step(x_batch_test, y_batch_test, step_test, writer=None):
            """
             Evaluates model on a dev set
            """
            feed_dict = {
                cnn.input_x: x_batch_test,
                cnn.input_y: y_batch_test,
                cnn.dropout_keep_prob: 1.0
            }
            _, _, summaries, loss, accuracy, crr, precision, recall = \
                sess.run([cnn.precision_op, cnn.recall_op, test_summary_op, cnn.loss,
                          cnn.accuracy, cnn.correct, cnn.precision, cnn.recall], feed_dict)
            time_str = datetime.datetime.now().isoformat()
            print("{}: step {}, loss {:g}, acc {:g}, prc {:g}, rcl {:g}".
                  format(time_str, step_test, loss, accuracy, precision, recall))
            if writer:
                writer.add_summary(summaries, step_test)
            return np.sum(crr)
        
        data_batch, label_batch = data_helpers.read_TFRecord(FLAGS.data_file, batch_size=FLAGS.batch_size)
        coord = tf.train.Coordinator()
        threads = tf.train.start_queue_runners(coord=coord)
        for step in range(FLAGS.num_epochs):
            
            try:
                while not coord.should_stop() and i<1:
                    # just plot one batch size            
                    data, label = sess.run([data_batch, label_batch])
                    print('data', data)
                    print('label', label)
                    i+=1
                    
            except tf.errors.OutOfRangeError:
                print('done!')
            finally:
                coord.request_stop()
            coord.join(threads)

#        # Generate batches
#        batches = data_helpers.batch_generator(
#            list(zip(x_train, y_train)), FLAGS.batch_size, FLAGS.num_epochs)
#
#        # Training loop. For each batch...
#        for batch in batches:
#            x_batch, y_batch = zip(*batch)
#            train_step(x_batch, y_batch)
#            current_step = tf.train.global_step(sess, global_step)
#            if current_step % FLAGS.evaluate_every == 0:
#                print("\nEvaluation:")
#                dev_batches = data_helpers.batch_generator(list(zip(x_dev, y_dev)), FLAGS.batch_size * 2)
#
#                for dev_batch in dev_batches:
#                    x_dev_batch, y_dev_batch = zip(*dev_batch)
#                    dev_step(x_dev_batch, y_dev_batch, writer=dev_summary_writer)
#                print("\n")
#                # dev_step(x_dev, y_dev, writer=dev_summary_writr)
#            if current_step % FLAGS.checkpoint_every == 0:
#                path = saver.save(sess, checkpoint_prefix, global_step=current_step)
#                print("Saved model checkpoint to {}\n".format(path))
#
            
#        # embedding summaries
#        summary_dir = os.path.abspath(os.path.join(FLAGS.log_dir))
#        summary_writer = tf.summary.FileWriter(test_summary_dir)
#        # projector embedding
#        config = projector.ProjectorConfig()
#        embedding = config.embeddings.add()
#        embedding.tensor_name = cnn.W.name
#        embedding.metadata_path = os.path.abspath(os.path.join(FLAGS.log_dir, 'metadata.tsv'))
#        projector.visualize_embeddings(summary_writer, config)
#
#        print("\n Testing:")
#        dev_batches = data_helpers.batch_generator(list(zip(x_dev, y_dev)), FLAGS.batch_size)
#        step = 0
#        true_correct = 0
#        for dev_batch in dev_batches:
#            x_dev_batch, y_dev_batch = zip(*dev_batch)
#            correct = test_step(x_dev_batch, y_dev_batch, step, writer=test_summary_writer)
#            true_correct += np.sum(correct)
#            step += 1
#
#        numer_iter = int((len(y_dev) - 1) / FLAGS.batch_size) + 1
#        print('%s: total accuracy @ 3 = %.3f' %
#              (datetime.datetime.now().isoformat(), true_correct / (numer_iter * FLAGS.batch_size)))
