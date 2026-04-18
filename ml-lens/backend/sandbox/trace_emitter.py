def build_trace_code(params: dict) -> str:
    """
    Generate a self-contained Python script that builds a minimal PyTorch model,
    runs a forward pass, captures tensor snapshots, and prints JSON to stdout.
    """
    d_model = params["d_model"]
    num_heads = params["num_heads"]
    d_ff = params["d_ff"]
    seq_len = params["seq_len"]
    d_k = d_model // num_heads

    # Validate divisibility
    if d_model % num_heads != 0:
        raise ValueError(
            f"d_model ({d_model}) must be divisible by num_heads ({num_heads})"
        )

    script = f'''
import torch
import torch.nn as nn
import json

torch.manual_seed(42)

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, num_heads, d_k):
        super().__init__()
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_k
        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)

    def forward(self, x):
        B, T, D = x.shape
        Q = self.q_proj(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)
        K = self.k_proj(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)
        V = self.v_proj(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)
        scores = torch.matmul(Q, K.transpose(-2, -1)) / (self.d_k ** 0.5)
        attn = torch.softmax(scores, dim=-1)
        context = torch.matmul(attn, V).transpose(1, 2).contiguous()
        context = context.view(B, T, self.d_model)
        out = self.out_proj(context)
        return out

class TransformerLayer(nn.Module):
    def __init__(self, d_model, num_heads, d_ff):
        super().__init__()
        self.embedding = nn.Embedding(1000, d_model)
        self.attention = MultiHeadAttention(d_model, num_heads, d_model // num_heads)
        self.norm1 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.ReLU(),
            nn.Linear(d_ff, d_model)
        )
        self.norm2 = nn.LayerNorm(d_model)

    def forward(self, x):
        embedded = self.embedding(x)
        attn_out = self.attention(embedded)
        normalized = self.norm1(attn_out + embedded)
        ffn_out = self.ffn(normalized)
        out = self.norm2(ffn_out + normalized)
        return out

# Build model and capture snapshots
model = TransformerLayer({d_model}, {num_heads}, {d_ff})
snapshots = []

def make_hook(component_id, input_shapes, output_shapes):
    def hook(module, input, output):
        input_t = input[0] if input else torch.tensor([])
        output_t = output if isinstance(output, torch.Tensor) else output[0]

        input_shape = str(tuple(input_t.shape))
        output_shape = str(tuple(output_t.shape))

        input_flat = input_t.flatten().detach().cpu()[:4].tolist()
        output_flat = output_t.flatten().detach().cpu()[:4].tolist()

        snapshots.append({{
            "component_id": component_id,
            "input_shape": input_shape,
            "output_shape": output_shape,
            "input_sample": input_flat,
            "output_sample": output_flat,
            "operation_note": f"{{component_id}} forward pass"
        }})
    return hook

model.embedding.register_forward_hook(make_hook("embedding", ["(B,T)"], ["(B,T,D)"]))
model.attention.register_forward_hook(make_hook("attention", ["(B,T,D)"], ["(B,T,D)"]))
model.ffn.register_forward_hook(make_hook("ffn", ["(B,T,D)"], ["(B,T,D)"]))
model.norm2.register_forward_hook(make_hook("norm", ["(B,T,D)"], ["(B,T,D)"]))

# Forward pass with synthetic input
x = torch.randint(0, 1000, (1, {seq_len}))
model.eval()
with torch.no_grad():
    _ = model(x)

# Output JSON
output = {{
    "snapshots": snapshots,
    "params": {{"d_model": {d_model}, "num_heads": {num_heads}, "d_ff": {d_ff}, "seq_len": {seq_len}, "d_k": {d_k}}}
}}
print(json.dumps(output))
'''
    return script
