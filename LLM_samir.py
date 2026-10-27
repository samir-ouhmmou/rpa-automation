# TP 5 : LLM - Découverte pratique d'un LLM (GPT-2)
# Installation : pip install transformers torch sentencepiece matplotlib seaborn

# %% 1. Introduction et préparation
# GPT-2 (OpenAI, 2019) : modèle Transformer "decoder-only", pré-entraîné pour
# prédire le token suivant (génération auto-régressive). Version "gpt2" = 124M paramètres.
import torch
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from transformers import AutoTokenizer, AutoModel, AutoModelForCausalLM

# %% 2. Tokenisation et embeddings
tokenizer = AutoTokenizer.from_pretrained("gpt2")
# attn_implementation="eager" est nécessaire pour récupérer les poids d'attention
model = AutoModel.from_pretrained("gpt2", attn_implementation="eager")
model.eval()


def clean(tokens):
    """Rend les tokens GPT-2 lisibles (Ġ = espace précédent)."""
    return [t.replace("Ġ", "_") for t in tokens]


sentence = "The cat sat on the mat because it was tired"
inputs = tokenizer(sentence, return_tensors="pt")
ids = inputs["input_ids"][0]
tokens = clean(tokenizer.convert_ids_to_tokens(ids))

print("Phrase :", sentence)
print("IDs    :", ids.tolist())
print("Tokens :", tokens)

# --- Embeddings ---
with torch.no_grad():
    outputs = model(**inputs, output_attentions=True, output_hidden_states=True)

# Embeddings statiques (table d'embedding, avant tout contexte)
static_emb = model.get_input_embeddings()(ids).detach()          # (n_tokens, 768)
# Embeddings contextuels (dernière couche)
context_emb = outputs.last_hidden_state[0]                        # (n_tokens, 768)
print("Shape embeddings :", static_emb.shape)


def cosine_matrix(emb):
    emb = emb / emb.norm(dim=1, keepdim=True)
    return (emb @ emb.T).numpy()


fig, axes = plt.subplots(1, 2, figsize=(16, 6))
for ax, emb, title in zip(
    axes,
    [static_emb, context_emb],
    ["Similarité cosinus - embeddings statiques", "Similarité cosinus - embeddings contextuels (dernière couche)"],
):
    sns.heatmap(cosine_matrix(emb), xticklabels=tokens, yticklabels=tokens,
                cmap="viridis", annot=True, fmt=".2f", ax=ax, annot_kws={"size": 7})
    ax.set_title(title)
plt.tight_layout()
plt.show()

# %% 3. Génération de texte simple
lm = AutoModelForCausalLM.from_pretrained("gpt2")
lm.eval()

prompt = "Artificial intelligence is"
prompt_ids = tokenizer(prompt, return_tensors="pt")["input_ids"]

# 3a. Génération complète
torch.manual_seed(0)
generated = lm.generate(
    prompt_ids,
    max_new_tokens=25,
    do_sample=True,
    top_k=50,
    temperature=0.8,
    pad_token_id=tokenizer.eos_token_id,
)
print("\nTexte généré :\n", tokenizer.decode(generated[0]))

# 3b. Observer comment le modèle choisit les tokens suivants (top-5 à chaque étape)
print("\n--- Choix token par token (greedy) ---")
cur = prompt_ids.clone()
for step in range(8):
    with torch.no_grad():
        logits = lm(cur).logits[0, -1]
    probs = torch.softmax(logits, dim=-1)
    top = torch.topk(probs, 5)
    cands = [(tokenizer.decode(i), f"{p:.3f}") for i, p in zip(top.indices, top.values)]
    chosen = top.indices[0].unsqueeze(0).unsqueeze(0)
    print(f"Étape {step+1}: choisi={tokenizer.decode(chosen[0])!r}  top-5={cands}")
    cur = torch.cat([cur, chosen], dim=1)
print("Résultat greedy :", tokenizer.decode(cur[0]))

# %% 4. Visualisation simplifiée de l'attention
# outputs.attentions : tuple de 12 couches, chacune (batch, heads=12, n_tokens, n_tokens)
attentions = outputs.attentions


def plot_attention(attn, toks, title):
    plt.figure(figsize=(7, 6))
    sns.heatmap(attn, xticklabels=toks, yticklabels=toks, cmap="Blues", square=True)
    plt.xlabel("Token regardé (clé)")
    plt.ylabel("Token qui regarde (requête)")
    plt.title(title)
    plt.tight_layout()
    plt.show()


layer, head = 5, 3
plot_attention(attentions[layer][0, head].numpy(), tokens, f"Attention - couche {layer}, tête {head}")

# Moyenne sur toutes les têtes de la dernière couche
plot_attention(attentions[-1][0].mean(dim=0).numpy(), tokens, "Attention moyenne - dernière couche")
# Remarque : la matrice est triangulaire inférieure (masque causal) :
# un token ne peut regarder que les tokens précédents.

# %% 5. Discussion et analyse
def attention_received(text, layer=-1):
    """Attention moyenne (toutes têtes, toutes requêtes) reçue par chaque token."""
    inp = tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        out = model(**inp, output_attentions=True)
    att = out.attentions[layer][0].mean(dim=0)       # (n, n)
    received = att.sum(dim=0) / torch.arange(att.shape[0], 0, -1)  # normalise par nb de requêtes possibles
    toks = clean(tokenizer.convert_ids_to_tokens(inp["input_ids"][0]))
    return toks, received.numpy()


phrases = [
    "The cat sat on the mat because it was tired",
    "The doctor said that the patient needs rest",
    "Paris is the capital of France",
]
fig, axes = plt.subplots(len(phrases), 1, figsize=(10, 3 * len(phrases)))
for ax, p in zip(axes, phrases):
    toks, rec = attention_received(p)
    ax.bar(range(len(toks)), rec)
    ax.set_xticks(range(len(toks)))
    ax.set_xticklabels(toks, rotation=45)
    ax.set_title(p)
plt.tight_layout()
plt.show()

# Pistes pour la discussion :
# - Le premier token (ou <|endoftext|>) capte souvent une grande part de l'attention
#   ("attention sink") : il sert de point d'ancrage et n'est pas forcément informatif.
# - Dans certaines têtes, "it" regarde "cat" : la self-attention modélise la coréférence.
# - Les mots de fonction (the, on, was) reçoivent en général moins d'attention que
#   les mots porteurs de sens (cat, tired, capital).
# - Lien avec la théorie : texte -> tokenisation (BPE) -> embeddings -> self-attention
#   (Q, K, V, masque causal) -> distribution sur le vocabulaire -> token suivant,
#   répété en boucle (génération auto-régressive).