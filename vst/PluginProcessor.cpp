#include "PluginProcessor.h"
#include "PluginEditor.h"

namespace {
constexpr const char* kIDs[BassDriverAudioProcessor::kNumParams] = {
    "presence", "drive", "blend", "bass", "treble", "mid", "level", "mode"};
constexpr const char* kNames[BassDriverAudioProcessor::kNumParams] = {
    "Presence", "Drive", "Blend", "Bass", "Treble", "Mid", "Level", "Mode"};
constexpr float kDefaults[BassDriverAudioProcessor::kNumParams] = {
    0.5f, 0.35f, 1.0f, 0.5f, 0.5f, 0.5f, 0.6f, 0.0f};
}  // namespace

BassDriverAudioProcessor::BassDriverAudioProcessor()
    : AudioProcessor(BusesProperties()
                         .withInput("Input", juce::AudioChannelSet::stereo(), true)
                         .withOutput("Output", juce::AudioChannelSet::stereo(), true)),
      apvts(*this, nullptr, "params", createParameterLayout()) {}

juce::AudioProcessorValueTreeState::ParameterLayout
BassDriverAudioProcessor::createParameterLayout() {
    juce::AudioProcessorValueTreeState::ParameterLayout layout;
    for (int i = 0; i < 7; ++i) {
        layout.add(std::make_unique<juce::AudioParameterFloat>(
            juce::ParameterID{kIDs[i], 1}, kNames[i],
            juce::NormalisableRange<float>(0.0f, 1.0f), kDefaults[i]));
    }
    layout.add(std::make_unique<juce::AudioParameterChoice>(
        juce::ParameterID{kIDs[7], 1}, kNames[7],
        juce::StringArray{"V1 late (2004+)", "V1 early (<=2003)", "V2 (2016+)"},
        0));
    return layout;
}

void BassDriverAudioProcessor::prepareToPlay(double sampleRate, int) {
    const size_t sz = Bddi_state_size((float)sampleRate);
    stateMem.assign(2 * sz, 0.0f);
    core[0] = Bddi_init(&stateMem[0], sz, (float)sampleRate);
    core[1] = Bddi_init(&stateMem[sz], sz, (float)sampleRate);
    for (auto*& c : core) {
        if (c) Bddi_reset(c);
    }
    for (int i = 0; i < kNumParams; ++i) lastP[i] = -1.0f;  /* force push */
    pushParams();
}

void BassDriverAudioProcessor::releaseResources() {}

void BassDriverAudioProcessor::pushParams() {
    for (int i = 0; i < kNumParams; ++i) {
        const float v = apvts.getRawParameterValue(kIDs[i])->load();
        if (v != lastP[i]) {
            for (auto*& c : core) {
                if (c) Bddi_set_param(c, (BddiParam)i, v);
            }
            lastP[i] = v;
        }
    }
}

void BassDriverAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer,
                                            juce::MidiBuffer&) {
    juce::ScopedNoDenormals noDenormals;
    pushParams();

    const int n = buffer.getNumSamples();
    const int nch = juce::jmin(2, buffer.getNumChannels());
    float peak = 0.0f;
    for (int c = 0; c < nch; ++c) {
        float* x = buffer.getWritePointer(c);
        Bddi* b = core[c];
        if (!b) continue;
        for (int i = 0; i < n; ++i) {
            const float in = x[i];
            if (std::abs(in) > peak) peak = std::abs(in);
            float y = 0.0f;
            Bddi_process(b, in, &y);
            x[i] = y;
        }
    }
    inMeter.store(peak);
}

bool BassDriverAudioProcessor::isBusesLayoutSupported(const BusesLayout& l) const {
    const auto& in = l.getMainInputChannelSet();
    const auto& out = l.getMainOutputChannelSet();
    if (in != out) return false;
    return in == juce::AudioChannelSet::mono() || in == juce::AudioChannelSet::stereo();
}

juce::AudioProcessorEditor* BassDriverAudioProcessor::createEditor() {
    return new BassDriverAudioProcessorEditor(*this);
}

void BassDriverAudioProcessor::getStateInformation(juce::MemoryBlock& destData) {
    auto state = apvts.copyState();
    std::unique_ptr<juce::XmlElement> xml(state.createXml());
    copyXmlToBinary(*xml, destData);
}

void BassDriverAudioProcessor::setStateInformation(const void* data, int sizeInBytes) {
    std::unique_ptr<juce::XmlElement> xml(getXmlFromBinary(data, sizeInBytes));
    if (xml && xml->hasTagName(apvts.state.getType()))
        apvts.replaceState(juce::ValueTree::fromXml(*xml));
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() {
    return new BassDriverAudioProcessor();
}
