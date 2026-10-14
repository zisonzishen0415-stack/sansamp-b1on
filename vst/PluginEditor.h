#pragma once
#include <JuceHeader.h>
#include "PluginProcessor.h"

class BassDriverAudioProcessorEditor : public juce::AudioProcessorEditor {
public:
    explicit BassDriverAudioProcessorEditor(BassDriverAudioProcessor&);
    ~BassDriverAudioProcessorEditor() override = default;

    void paint(juce::Graphics&) override;
    void resized() override;

private:
    BassDriverAudioProcessor& proc;

    juce::Slider knobs[BassDriverAudioProcessor::kNumParams];
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment>
        knobAtt[BassDriverAudioProcessor::kNumParams];
    juce::Label nameLabels[BassDriverAudioProcessor::kNumParams];

    juce::ComboBox modeBox;
    std::unique_ptr<juce::AudioProcessorValueTreeState::ComboBoxAttachment> modeAtt;

    juce::Image coverImage;                 /* our chibi, same art as the ZDL */
    juce::Rectangle<int> coverBounds;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(BassDriverAudioProcessorEditor)
};
