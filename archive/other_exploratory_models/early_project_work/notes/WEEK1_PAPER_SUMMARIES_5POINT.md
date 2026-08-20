# Week 1 Paper Summaries - 5 Point Format

Project: Computational Neuropathic Pain Model  
Focus: DRG-SDH circuit, GABA SDH Group 3, neuropathic pain disinhibition

---

## Paper 1: Costigan, Scholz & Woolf 2009 - Neuropathic pain overview

1. Biological question addressed:  
What makes neuropathic pain different from normal protective nociceptive pain?

2. Method used:  
Review article summarising clinical and experimental evidence.

3. Key quantitative result:  
Neuropathic pain affects a large population clinically and is often resistant to standard analgesics.

4. Effect on model design:  
The model should not only simulate normal stimulus-evoked pain. It should also represent hyperexcitability, spontaneous firing, allodynia, and hyperalgesia.

5. Unanswered question:  
Which exact channel or circuit change is most responsible in a specific neuropathic condition?

---

## Paper 2: Dubin & Patapoutian 2010 - Nociceptors and DRG ion channels

1. Biological question addressed:  
How do nociceptors detect painful mechanical, thermal, and chemical stimuli?

2. Method used:  
Review of sensory neuron subtypes, receptors, and ion channels.

3. Key quantitative result:  
Small-diameter C fibres and A-delta fibres are the main nociceptive subtypes.

4. Effect on model design:  
The DRG part of the model should focus on small nociceptive fibres and channels such as sodium channels and TRP channels.

5. Unanswered question:  
How should channel expression differences across DRG subtypes be converted into exact NEURON conductance values?

---

## Paper 3: Todd 2010 / central sensitisation literature - SDH circuit

1. Biological question addressed:  
How does the spinal dorsal horn process pain signals?

2. Method used:  
Neuroanatomical and circuit-level review.

3. Key quantitative result:  
SDH contains excitatory projection neurons, excitatory interneurons, and inhibitory GABA/glycine interneurons.

4. Effect on model design:  
For Group 3, GABA inhibitory neurons are essential because reduced inhibition can amplify SDH output in neuropathic pain.

5. Unanswered question:  
Which inhibitory SDH subtype contributes most strongly to pathological disinhibition?

---

## Paper 4: Hone & McIntosh 2018 - nAChRs in neuropathic and inflammatory pain

1. Biological question addressed:  
How do nicotinic acetylcholine receptor subtypes modulate pain?

2. Method used:  
Review of receptor subtype expression, pharmacology, EC50 values, and pain models.

3. Key quantitative result:  
Different nAChR subtypes have different ACh sensitivity and desensitisation kinetics.

4. Effect on model design:  
nAChR models should not all use the same kinetics. Alpha7 and alpha9-like receptors may need Markov-style desensitisation, while alpha3-containing receptors may be simpler HH-style conductances.

5. Unanswered question:  
In the DRG-SDH circuit, does cholinergic modulation mainly suppress DRG excitability or alter transmitter release at the terminal?

---

## Paper 5: Medlock et al. 2022 - Spinal dorsal horn network model

1. Biological question addressed:  
How does the spinal dorsal horn network process normal and chronic pain-related sensory input?

2. Method used:  
Multiscale NEURON/NetPyNE computational model of SDH excitatory and inhibitory neuron populations.

3. Key quantitative result:  
The model reproduces characteristic firing patterns of SDH neuron classes and network-level responses to sensory input.

4. Effect on model design:  
ModelDB 267056 should be used as the SDH template rather than building the SDH circuit from scratch.

5. Unanswered question:  
How will adding DRG-specific disease-channel changes alter SDH output and GABA-mediated inhibition balance?

---

## Paper 6: Farooqui et al. 2024 - DRG pseudounipolar neuron and axon model

1. Biological question addressed:  
How do DRG pseudounipolar morphology and spatial distribution affect selective activation of sensory neurons?

2. Method used:  
Python/NEURON model of DRG pseudounipolar neuron and axon.

3. Key quantitative result:  
The model can instantiate sensory DRG axon/neuron structures across a fibre diameter range.

4. Effect on model design:  
Farooqui ModelDB 2018004 can be used as a fallback DRG morphology/electrophysiology template if NeuroMorpho DRG morphology is unsuitable.

5. Unanswered question:  
How should this mainly sensory stimulation model be adapted for nociceptive neuropathic pain channels such as Nav1.7/Nav1.8/Nav1.9?

