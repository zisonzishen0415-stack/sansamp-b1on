#pragma once
#include <JuceHeader.h>
#include "bddi.h"
#include <atomic>
#include <vector>

/* BassDriver VST3: thin JUCE wrapper around the same core/bddi.c that the
 * B1on ZDL build uses -- one Bddi instance per channel. */
class BassDriverAudioProcessor : public juce::AudioProcessor {
public:
    BassDriverAudioProcessor();
    ~BassDriverAudioProcessor() override = default;

    void prepareToPlay(double sampleRate, int samplesPerBlock) override;
    void releaseResources() override;
    void processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer&) override;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }
    const juce::String getName() const override { return "BassDriver"; }
    bool acceptsMidi() const override { return false; }
    bool producesMidi() const override { return false; }
    double getTailLengthSeconds() const override { return 0.1; }
    bool isBusesLayoutSupported(const BusesLayout& layouts) const override;

    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override { return "Default"; }
    void changeProgramName(int, const juce::String&) override {}

    void getStateInformation(juce::MemoryBlock& destData) override;
    void setStateInformation(const void* data, int sizeInBytes) override;

    juce::AudioProcessorValueTreeState apvts;

    std::atomic<float> inMeter{0.0f};      /* audio thread -> editor */

    static constexpr int kNumParams = 8;

private:
    juce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout();
    void pushParams();
    std::vector<float> stateMem;           /* owns both cores' state memory */
    float lastP[kNumParams] = {};
    Bddi* core[2] = {nullptr, nullptr};
};
