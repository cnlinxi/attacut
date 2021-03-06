import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence

from slimcut import utils
from . import CharacterSeqBaseModel, ConvolutionLayer


class Model(CharacterSeqBaseModel):
    def __init__(self, data_config, model_config="emb:32|conv:48|cell:16|bi:1|l1:16|do:0.1"):
        super(Model, self).__init__()

        no_chars = data_config['num_tokens']

        config = utils.parse_model_params(model_config)
        emb_dim = config['emb']
        conv_filters = config['conv']
        dropout_rate = config.get("do", 0)

        self.embeddings = nn.Embedding(
            no_chars,
            emb_dim,
            padding_idx=0
        )

        self.dropout= torch.nn.Dropout(p=dropout_rate)


        bidirection = bool(config.get("bi", 0))

        self.lstm = nn.LSTM(
            emb_dim,
            config['cell'],
            batch_first=True,
            bidirectional=bidirection
        )

        out_dim = config['cell']*2 if bidirection else config['cell']

        self.conv1 = ConvolutionLayer(out_dim, conv_filters, 5)

        self.linear1 = nn.Linear(conv_filters, config['l1'])
        self.linear2 = nn.Linear(config['l1'], 1)

        self.model_params = model_config

    def forward(self, inputs):
        x, seq_lengths = inputs

        embedding = self.embeddings(x)
        packed_input = pack_padded_sequence(
            embedding,
            seq_lengths.cpu().numpy(),
            batch_first=True
        )

        packed_output, (ht, ct) = self.lstm(packed_input)
        output, input_sizes = pad_packed_sequence(packed_output, batch_first=True)

        output = F.relu(self.conv1(output.permute(0, 2, 1)).permute(0, 2, 1))

        out = F.relu(self.linear1(output))
        out = self.linear2(out)
        out = out.view(-1)

        return out